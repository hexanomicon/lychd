package main

import (
	"net/netip"

	"golang.zx2c4.com/wireguard/tun"
	"gvisor.dev/gvisor/pkg/tcpip"
	"gvisor.dev/gvisor/pkg/tcpip/header"
)

// Apply the service grant before the network stack can process decrypted IP
// traffic (including its automatic ICMP and closed-port responses).
type serviceDevice struct {
	tun.Device
	source, destination tcpip.Address
	port                uint16
}

func exactService(d tun.Device, peer netip.Addr, service netip.AddrPort) *serviceDevice {
	return &serviceDevice{d, tcpip.AddrFrom4(peer.As4()), tcpip.AddrFrom4(service.Addr().As4()), service.Port()}
}

func (d *serviceDevice) allows(packet []byte) bool {
	ip := header.IPv4(packet)
	if !ip.IsValid(len(packet)) || ip.HeaderLength() != header.IPv4MinimumSize ||
		ip.More() || ip.FragmentOffset() != 0 || ip.TransportProtocol() != header.TCPProtocolNumber ||
		ip.SourceAddress() != d.source || ip.DestinationAddress() != d.destination {
		return false
	}
	tcp := header.TCP(ip.Payload())
	return len(tcp) >= header.TCPMinimumSize && tcp.DataOffset() >= header.TCPMinimumSize &&
		int(tcp.DataOffset()) <= len(tcp) && tcp.DestinationPort() == d.port
}

func (d *serviceDevice) Write(buffers [][]byte, offset int) (int, error) {
	for i, buffer := range buffers {
		if offset < 0 || offset > len(buffer) || !d.allows(buffer[offset:]) {
			continue
		}
		if _, err := d.Device.Write(buffers[i:i+1], offset); err != nil {
			return i, err
		}
	}
	return len(buffers), nil
}
