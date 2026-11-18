package main

import (
	"bufio"
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/netip"
	"os"
	"regexp"
	"strconv"
	"strings"
)

var peerName = regexp.MustCompile(`^[a-z][a-z0-9-]{0,31}$`)

type grant struct {
	Peer       string     `json:"peer"`
	Address    netip.Addr `json:"address"`
	Port       uint16     `json:"udp_port"`
	PublicKey  string     `json:"server_public_key"`
	Generation string     `json:"generation"`
	Active     bool       `json:"active"`

	peerKey string
	road    *road
}

type manager struct {
	service netip.AddrPort
	backend backendTarget
	session string
	grants  map[string]*grant
}

func nonce() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func privateIP(a netip.Addr) bool { return a.Is4() && a.IsPrivate() }

func (m *manager) admit(args []string) (*grant, error) {
	if len(args) != 5 || args[0] != m.session {
		return nil, errors.New("expected admit SESSION PEER PRIVATE_IPV4 PUBLIC_KEY UDP_PORT")
	}
	name := args[1]
	if !peerName.MatchString(name) {
		return nil, errors.New("invalid peer name")
	}
	address, err := netip.ParseAddr(args[2])
	if err != nil || !privateIP(address) || address == m.service.Addr() {
		return nil, errors.New("peer needs a distinct private IPv4 address")
	}
	key, err := base64.StdEncoding.Strict().DecodeString(args[3])
	if err != nil || len(key) != 32 || base64.StdEncoding.EncodeToString(key) != args[3] {
		return nil, errors.New("invalid WireGuard public key")
	}
	port, err := strconv.ParseUint(args[4], 10, 16)
	if err != nil || port < 1024 {
		return nil, errors.New("expected an unprivileged UDP port")
	}
	active := 0
	for _, g := range m.grants {
		if g.Peer == name || g.Address == address || g.peerKey == args[3] {
			return nil, errors.New("peer identity, key or address already used in this session")
		}
		if g.Active {
			active++
			if uint16(port) == g.Port {
				return nil, errors.New("UDP port already admitted")
			}
		}
	}
	if active >= 8 || len(m.grants) >= 1024 {
		return nil, errors.New("session peer limit reached")
	}
	road, pub, err := startRoad(m.service, m.backend, address, key, uint16(port))
	if err != nil {
		return nil, err
	}
	g := &grant{name, address, uint16(port), pub, nonce(), true, args[3], road}
	m.grants[name] = g
	return g, nil
}

func (m *manager) revoke(args []string) (*grant, error) {
	if len(args) != 2 {
		return nil, errors.New("expected revoke PEER GENERATION")
	}
	g := m.grants[args[0]]
	if g == nil || g.Generation != args[1] {
		return nil, errors.New("unknown peer or stale generation")
	}
	if g.Active {
		g.road.close()
		g.road = nil
		g.Active = false
	}
	return g, nil
}

func (m *manager) command(fields []string) (any, error) {
	if len(fields) > 0 {
		switch fields[0] {
		case "admit":
			return m.admit(fields[1:])
		case "revoke":
			return m.revoke(fields[1:])
		case "status":
			if len(fields) == 1 {
				return m.grants, nil
			}
		}
	}
	return nil, errors.New("expected admit, revoke or status")
}

func serveConsole(input io.Reader, output io.Writer, service netip.AddrPort, backend backendTarget) error {
	m := manager{service, backend, nonce(), make(map[string]*grant)}
	defer func() {
		for _, g := range m.grants {
			if g.Active {
				g.road.close()
			}
		}
	}()
	encoder := json.NewEncoder(output)
	if err := encoder.Encode(map[string]any{"session": m.session, "service": service, "loopback_port": backend.port, "backend_name": backend.tlsConfig.ServerName}); err != nil {
		return err
	}
	lines := bufio.NewScanner(input)
	lines.Buffer(make([]byte, 4096), 4096)
	for lines.Scan() {
		result, err := m.command(strings.Fields(lines.Text()))
		if err != nil {
			result = map[string]string{"error": err.Error()}
		}
		if err := encoder.Encode(result); err != nil {
			return err
		}
	}
	return lines.Err()
}

func main() {
	serviceArg := flag.String("service", "", "one tunnel-private IPv4 address and TCP port")
	backend := flag.Uint("loopback-port", 0, "one local service TCP port on 127.0.0.1")
	certFile := flag.String("backend-cert", "", "public PEM certificate of the authorized loopback TLS service")
	name := flag.String("backend-name", "localhost", "expected certificate hostname (no DNS resolution)")
	flag.Parse()
	service, err := netip.ParseAddrPort(*serviceArg)
	if err != nil || !privateIP(service.Addr()) || service.Port() == 0 || *backend == 0 || *backend > 65535 || *certFile == "" || *name == "" || flag.NArg() != 0 {
		fmt.Fprintln(os.Stderr, "expected --service PRIVATE_IPV4:PORT --loopback-port PORT --backend-cert PUBLIC_CERT.pem [--backend-name HOST]")
		os.Exit(2)
	}
	certificate, err := os.ReadFile(*certFile)
	if err != nil {
		fmt.Fprintln(os.Stderr, "cannot read backend certificate")
		os.Exit(2)
	}
	target, err := pinnedBackend(uint16(*backend), *name, certificate)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if err := serveConsole(os.Stdin, os.Stdout, service, target); err != nil {
		fmt.Fprintln(os.Stderr, "owner console closed:", err)
		os.Exit(1)
	}
}
