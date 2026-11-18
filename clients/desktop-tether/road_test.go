package main

import (
	"bytes"
	"context"
	"crypto/ecdh"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"math/big"
	"net"
	"net/netip"
	"os"
	"strings"
	"testing"
	"time"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun/netstack"
	"gvisor.dev/gvisor/pkg/tcpip/header"
)

func endpoint(t *testing.T, port uint16, name, address string, m *manager) (*grant, *netstack.Net, []string) {
	t.Helper()
	private, err := ecdh.X25519().GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	pub := base64.StdEncoding.EncodeToString(private.PublicKey().Bytes())
	args := []string{m.session, name, address, pub, fmt.Sprint(port)}
	g, err := m.admit(args)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if _, err := m.revoke([]string{name, g.Generation}); err != nil {
			t.Error(err)
		}
	})
	tun, stack, err := netstack.CreateNetTUN([]netip.Addr{netip.MustParseAddr(address)}, nil, 1420)
	if err != nil {
		t.Fatal(err)
	}
	dev := device.NewDevice(tun, conn.NewDefaultBind(), device.NewLogger(device.LogLevelSilent, ""))
	t.Cleanup(dev.Close)
	serverKey, err := base64.StdEncoding.DecodeString(g.PublicKey)
	if err != nil {
		t.Fatal(err)
	}
	// The test peer deliberately sends ALL destinations to this server to test
	// its enforcement independently of the client's AllowedIPs policy.
	config := fmt.Sprintf("private_key=%x\npublic_key=%x\nallowed_ip=0.0.0.0/0\nendpoint=127.0.0.1:%d\n",
		private.Bytes(), serverKey, g.Port)
	if err := dev.IpcSet(config); err != nil {
		t.Fatal("test client rejected WireGuard configuration")
	}
	if err := dev.Up(); err != nil {
		t.Fatal(err)
	}
	return g, stack, args
}

func freeUDP(t *testing.T) uint16 {
	t.Helper()
	c, err := net.ListenUDP("udp4", &net.UDPAddr{IP: net.IPv4zero})
	if err != nil {
		t.Fatal(err)
	}
	defer c.Close()
	return uint16(c.LocalAddr().(*net.UDPAddr).Port)
}

func dial(t *testing.T, stack *netstack.Net, service netip.AddrPort) net.Conn {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	c, err := stack.DialContextTCPAddrPort(ctx, service)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { c.Close() })
	return c
}

func exchange(t *testing.T, c net.Conn, text string) {
	t.Helper()
	c.SetDeadline(time.Now().Add(5 * time.Second))
	if _, err := io.WriteString(c, text); err != nil {
		t.Fatal(err)
	}
	buf := make([]byte, len(text))
	if _, err := io.ReadFull(c, buf); err != nil || string(buf) != text {
		t.Fatalf("echo %q, %v", buf, err)
	}
}

func certificate(t *testing.T) (tls.Certificate, []byte) {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	template := &x509.Certificate{SerialNumber: big.NewInt(1), DNSNames: []string{"localhost"},
		NotBefore: time.Now().Add(-time.Minute), NotAfter: time.Now().Add(time.Hour),
		KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	der, err := x509.CreateCertificate(rand.Reader, template, template, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	return tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key}, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
}

func TestOfferedServiceAcrossTwoEncryptedPeers(t *testing.T) {
	cert, material := certificate(t)
	l, err := tls.Listen("tcp4", "127.0.0.1:0", &tls.Config{Certificates: []tls.Certificate{cert}, MinVersion: tls.VersionTLS13})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { l.Close() })
	accepted := make(chan struct{}, maxStreams+2)
	ended := make(chan struct{}, maxStreams+2)
	go func() {
		for {
			c, err := l.Accept()
			if err != nil {
				return
			}
			accepted <- struct{}{}
			go func() {
				io.Copy(c, c)
				c.Close()
				ended <- struct{}{}
			}()
		}
	}()
	service := netip.MustParseAddrPort("10.93.0.1:8443")
	backend, err := pinnedBackend(uint16(l.Addr().(*net.TCPAddr).Port), "localhost", material)
	if err != nil {
		t.Fatal(err)
	}
	m := manager{service, backend, nonce(), make(map[string]*grant)}
	g, stack, args := endpoint(t, freeUDP(t), "first", "10.93.0.2", &m)
	_, other, _ := endpoint(t, freeUDP(t), "second", "10.93.0.3", &m)
	first, second := dial(t, stack, service), dial(t, other, service)
	exchange(t, first, "first authenticated WireGuard path")
	exchange(t, second, "independent WireGuard path")
	<-accepted
	<-accepted
	ping, err := stack.DialPingAddr(g.Address, service.Addr())
	if err != nil {
		t.Fatal(err)
	}
	defer ping.Close()
	ping.SetReadDeadline(time.Now().Add(400 * time.Millisecond))
	echo := make(header.ICMPv4, header.ICMPv4MinimumSize)
	echo.SetType(header.ICMPv4Echo)
	echo.SetSequence(1)
	echo.SetChecksum(header.ICMPv4Checksum(echo, 0))
	if _, err := ping.Write(echo); err != nil {
		t.Fatal(err)
	}
	if _, err := ping.Read(make([]byte, 1500)); !errors.Is(err, os.ErrDeadlineExceeded) {
		t.Fatalf("unadmitted ICMP outcome: %v", err)
	}
	for _, destination := range []string{"10.93.0.1:8444", "10.93.0.3:8443", l.Addr().String()} {
		ctx, cancel := context.WithTimeout(context.Background(), 400*time.Millisecond)
		otherPort, err := stack.DialContextTCPAddrPort(ctx, netip.MustParseAddrPort(destination))
		cancel()
		if err == nil {
			otherPort.Close()
			t.Fatalf("unadmitted destination %s answered", destination)
		}
	}
	for index, value := range map[int]string{1: g.Peer, 2: g.Address.String(), 3: args[3], 4: fmt.Sprint(g.Port)} {
		private, err := ecdh.X25519().GenerateKey(rand.Reader)
		if err != nil {
			t.Fatal(err)
		}
		trial := []string{m.session, "distinct", "10.93.0.4", base64.StdEncoding.EncodeToString(private.PublicKey().Bytes()), fmt.Sprint(freeUDP(t))}
		trial[index] = value
		if _, err := m.admit(trial); err == nil {
			t.Fatalf("duplicate field %d admitted", index)
		}
	}
	if _, err := m.revoke([]string{g.Peer, "stale-generation"}); err == nil {
		t.Fatal("stale revoke acted")
	}
	exchange(t, first, "still active")
	if _, err := m.revoke([]string{g.Peer, g.Generation}); err != nil {
		t.Fatal(err)
	}
	select {
	case <-ended: // independently observe closure at the host service
	case <-time.After(3 * time.Second):
		t.Fatal("backend stream survived revocation")
	}
	first.SetDeadline(time.Now().Add(400 * time.Millisecond))
	io.WriteString(first, "revoked")
	if _, err := first.Read(make([]byte, 1)); err == nil {
		t.Fatal("revoked stream returned data")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 400*time.Millisecond)
	defer cancel()
	if c, err := stack.DialContextTCPAddrPort(ctx, service); err == nil {
		c.Close()
		t.Fatal("revoked peer opened another stream")
	}
	exchange(t, second, "survived revocation of first peer")
	checkStreamLimit(t, other, service, second, accepted)
	if _, err := m.admit(args); err == nil {
		t.Fatal("revoked admission replayed in this session")
	}
	// Re-start from the identical service coordinates and replay captured input.
	restarted := manager{service, m.backend, nonce(), make(map[string]*grant)}
	if _, err := restarted.admit(args); err == nil || len(restarted.grants) != 0 {
		t.Fatal("old grant restored after process restart")
	}
	select {
	case <-accepted:
		t.Fatal("unadmitted backend stream opened")
	default:
	}
}

func checkStreamLimit(t *testing.T, stack *netstack.Net, service netip.AddrPort, existing net.Conn, accepted <-chan struct{}) {
	t.Helper()
	// One stream is already active. Observe the TLS backend accept each permitted connection.
	for i := 1; i < maxStreams; i++ {
		c := dial(t, stack, service)
		exchange(t, c, "admitted within budget")
		<-accepted
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if excess, err := stack.DialContextTCPAddrPort(ctx, service); err == nil {
		defer excess.Close()
		excess.SetDeadline(time.Now().Add(2 * time.Second))
		io.WriteString(excess, "over budget")
		if _, err := excess.Read(make([]byte, 1)); err == nil {
			t.Fatal("excess stream reached backend")
		}
	}
	exchange(t, existing, "existing stream survives excess connection")
}

func TestConsoleStartsClosedAndRefusesMalformedCommands(t *testing.T) {
	var output bytes.Buffer
	_, public := certificate(t)
	backend, err := pinnedBackend(443, "localhost", public)
	if err != nil {
		t.Fatal(err)
	}
	err = serveConsole(strings.NewReader("status\nadmit old\nrevoke\nstatus\n"), &output, netip.MustParseAddrPort("10.93.0.1:443"), backend)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	var header map[string]any
	if len(lines) != 5 || json.Unmarshal([]byte(lines[0]), &header) != nil || header["session"] == nil ||
		lines[1] != "{}" || !strings.Contains(lines[2], "error") || !strings.Contains(lines[3], "error") || lines[4] != "{}" {
		t.Fatal("unexpected console output:", output.String())
	}
}

func TestBackendCertificateMismatchFencesApplicationBytes(t *testing.T) {
	_, expected := certificate(t)
	replacement, _ := certificate(t)
	l, err := tls.Listen("tcp4", "127.0.0.1:0", &tls.Config{Certificates: []tls.Certificate{replacement}, MinVersion: tls.VersionTLS13})
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	backend, err := pinnedBackend(uint16(l.Addr().(*net.TCPAddr).Port), "localhost", expected)
	if err != nil {
		t.Fatal(err)
	}
	received := make(chan int, 1)
	go func() {
		c, err := l.Accept()
		if err != nil {
			return
		}
		defer c.Close()
		c.SetReadDeadline(time.Now().Add(2 * time.Second))
		n, _ := c.Read(make([]byte, 1))
		received <- n
	}()
	client, incoming := net.Pipe()
	defer client.Close()
	go relay(context.Background(), incoming, backend)
	client.SetDeadline(time.Now().Add(2 * time.Second))
	if _, err := io.WriteString(client, "application credential"); err == nil {
		t.Fatal("forwarded to replacement service")
	}
	select {
	case n := <-received:
		if n != 0 {
			t.Fatal("replacement received peer bytes")
		}
	case <-time.After(3 * time.Second):
		t.Fatal("no backend observation")
	}
}
