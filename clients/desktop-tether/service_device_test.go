package main

import (
	"net/netip"
	"testing"

	"gvisor.dev/gvisor/pkg/tcpip/header"
)

func TestOnlyUnfragmentedIPv4TCPServicePacketsReachStack(t *testing.T) {
	d := exactService(nil, netip.MustParseAddr("10.0.0.2"), netip.MustParseAddrPort("10.0.0.1:8443"))
	packet := make([]byte, header.IPv4MinimumSize+header.TCPMinimumSize)
	ip := header.IPv4(packet)
	ip.Encode(&header.IPv4Fields{TotalLength: uint16(len(packet)), TTL: 64, Protocol: uint8(header.TCPProtocolNumber), SrcAddr: d.source, DstAddr: d.destination})
	tcp := header.TCP(ip.Payload())
	tcp.Encode(&header.TCPFields{SrcPort: 1025, DstPort: d.port, DataOffset: header.TCPMinimumSize})
	if !d.allows(packet) {
		t.Fatal("valid TCP service packet denied")
	}
	for _, mutate := range []func(header.IPv4){
		func(p header.IPv4) { p.SetFlagsFragmentOffset(header.IPv4FlagMoreFragments, 0) },
		func(p header.IPv4) { p.SetFlagsFragmentOffset(0, 8) },
		func(p header.IPv4) { p.SetDestinationAddress(d.source) },
		func(p header.IPv4) { p.SetSourceAddress(d.destination) },
		func(p header.IPv4) { header.TCP(p.Payload()).SetDestinationPort(22) },
		func(p header.IPv4) { p.SetHeaderLength(24) },
		func(p header.IPv4) { p[9] = uint8(header.UDPProtocolNumber) },
		func(p header.IPv4) { p[9] = uint8(header.ICMPv4ProtocolNumber) },
	} {
		p := append([]byte(nil), packet...)
		mutate(p)
		if d.allows(p) {
			t.Fatal("unadmitted packet reached stack")
		}
	}
	for i := 0; i < len(packet); i++ {
		if d.allows(packet[:i]) {
			t.Fatal("partial packet reached stack")
		}
	}
}
