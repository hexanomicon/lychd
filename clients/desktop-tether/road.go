// Package main provides the owner-operated desktop Tether offered-service profile.
package main

import (
	"bytes"
	"context"
	"crypto/ecdh"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"net"
	"net/netip"
	"sync"
	"time"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun/netstack"
)

const maxStreams = 32

type backendTarget struct {
	port      uint16
	tlsConfig *tls.Config
}

// The explicit leaf pin prevents a new process which inherits the same
// loopback port from receiving bytes. Normal TLS hostname and expiry checks apply.
func pinnedBackend(port uint16, name string, certificate []byte) (backendTarget, error) {
	block, rest := pem.Decode(certificate)
	if block == nil || block.Type != "CERTIFICATE" || len(bytes.TrimSpace(rest)) != 0 {
		return backendTarget{}, errors.New("expected one public service certificate")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil || cert.VerifyHostname(name) != nil {
		return backendTarget{}, errors.New("service certificate does not match backend name")
	}
	roots := x509.NewCertPool()
	roots.AddCert(cert)
	config := &tls.Config{MinVersion: tls.VersionTLS13, ServerName: name, RootCAs: roots,
		VerifyConnection: func(c tls.ConnectionState) error {
			if len(c.PeerCertificates) == 0 || !c.PeerCertificates[0].Equal(cert) {
				return errors.New("backend service certificate changed")
			}
			return nil
		},
	}
	return backendTarget{port, config}, nil
}

// A road has its own WireGuard device, in-memory TCP/IP stack and stream lifecycle.
// Only the fixed local service is dialled through the host network.
type road struct {
	device   *device.Device
	listener net.Listener
	cancel   context.CancelFunc
	done     chan struct{}
}

func startRoad(service netip.AddrPort, backend backendTarget, peer netip.Addr, publicKey []byte, port uint16) (*road, string, error) {
	privateKey, err := ecdh.X25519().GenerateKey(rand.Reader)
	if err != nil {
		return nil, "", err
	}
	remote, err := ecdh.X25519().NewPublicKey(publicKey)
	if err != nil {
		return nil, "", errors.New("invalid peer key")
	}
	if _, err := privateKey.ECDH(remote); err != nil {
		return nil, "", errors.New("invalid peer key")
	}
	tun, stack, err := netstack.CreateNetTUN([]netip.Addr{service.Addr()}, nil, 1420)
	if err != nil {
		return nil, "", err
	}
	dev := device.NewDevice(tun, conn.NewDefaultBind(), device.NewLogger(device.LogLevelSilent, ""))
	// IPC text is constructed only from typed values. Never log or return it.
	config := fmt.Sprintf("private_key=%s\nlisten_port=%d\npublic_key=%s\nallowed_ip=%s/32\n",
		hex.EncodeToString(privateKey.Bytes()), port, hex.EncodeToString(publicKey), peer)
	if err := dev.IpcSet(config); err != nil {
		dev.Close()
		return nil, "", errors.New("WireGuard configuration or UDP bind failed")
	}
	if err := dev.Up(); err != nil {
		dev.Close()
		return nil, "", errors.New("WireGuard startup failed")
	}
	listener, err := stack.ListenTCPAddrPort(service)
	if err != nil {
		dev.Close()
		return nil, "", errors.New("private service bind failed")
	}
	ctx, cancel := context.WithCancel(context.Background())
	r := &road{dev, listener, cancel, make(chan struct{})}
	go r.serve(ctx, peer, backend)
	return r, base64.StdEncoding.EncodeToString(privateKey.PublicKey().Bytes()), nil
}

func (r *road) serve(ctx context.Context, peer netip.Addr, backend backendTarget) {
	defer close(r.done)
	var streams sync.WaitGroup
	defer streams.Wait()
	slots := make(chan struct{}, maxStreams)
	for {
		c, err := r.listener.Accept()
		if err != nil {
			return
		}
		source, err := netip.ParseAddrPort(c.RemoteAddr().String())
		if err != nil || source.Addr() != peer {
			c.Close()
			continue
		}
		select {
		case slots <- struct{}{}:
			streams.Add(1)
			go func() {
				defer streams.Done()
				defer func() { <-slots }()
				relay(ctx, c, backend)
			}()
		default:
			c.Close()
		}
	}
}

func relay(ctx context.Context, incoming net.Conn, backend backendTarget) {
	defer incoming.Close()
	dialer := tls.Dialer{NetDialer: &net.Dialer{Timeout: 5 * time.Second}, Config: backend.tlsConfig}
	target, err := dialer.DialContext(ctx, "tcp4", net.JoinHostPort("127.0.0.1", fmt.Sprint(backend.port)))
	if err != nil {
		return
	}
	defer target.Close()
	stop := context.AfterFunc(ctx, func() {
		incoming.Close()
		target.Close()
	})
	defer stop()
	// Preserve TCP half-close. Revocation interrupts both copy directions.
	up := make(chan struct{})
	go func() {
		defer close(up)
		_, err := io.Copy(target, incoming)
		if err == nil {
			target.(*tls.Conn).CloseWrite()
		} else {
			target.Close()
		}
	}()
	_, err = io.Copy(incoming, target)
	if half, ok := incoming.(interface{ CloseWrite() error }); ok && err == nil {
		half.CloseWrite()
	} else {
		incoming.Close()
	}
	<-up
}

func (r *road) close() {
	r.cancel()
	r.listener.Close()
	r.device.Close()
	<-r.done
}
