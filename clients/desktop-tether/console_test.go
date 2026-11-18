package main

import (
	"bufio"
	"context"
	"crypto/ecdh"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

// Use this test executable as the real console in a separate OS process.
func TestConsoleChild(t *testing.T) {
	cert := os.Getenv("LYCHD_TETHER_TEST_CERT")
	if cert == "" {
		return
	}
	os.Args = []string{"desktop-tether", "--service", "10.93.0.1:8443", "--loopback-port", "18443", "--backend-cert", cert}
	flag.CommandLine = flag.NewFlagSet(os.Args[0], flag.ExitOnError)
	main()
	os.Exit(0)
}

type console struct {
	stdin  io.WriteCloser
	stdout *bufio.Scanner
	cmd    *exec.Cmd
}

func launchConsole(t *testing.T, cert string) *console {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	t.Cleanup(cancel)
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestConsoleChild$")
	cmd.Env = append(os.Environ(), "LYCHD_TETHER_TEST_CERT="+cert)
	cmd.Stderr = os.Stderr
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	return &console{stdin, bufio.NewScanner(stdout), cmd}
}

func (c *console) reply(t *testing.T, command string) map[string]any {
	t.Helper()
	if command != "" {
		if _, err := fmt.Fprintln(c.stdin, command); err != nil {
			t.Fatal(err)
		}
	}
	if !c.stdout.Scan() {
		t.Fatal("console exited before acknowledgement", c.stdout.Err())
	}
	var reply map[string]any
	if err := json.Unmarshal(c.stdout.Bytes(), &reply); err != nil {
		t.Fatal(err)
	}
	return reply
}

func (c *console) stop(t *testing.T) {
	t.Helper()
	if err := c.stdin.Close(); err != nil {
		t.Fatal(err)
	}
	if err := c.cmd.Wait(); err != nil {
		t.Fatal(err)
	}
}

func TestOwnerConsoleRejectsSavedAdmissionAfterRestart(t *testing.T) {
	_, public := certificate(t)
	cert := filepath.Join(t.TempDir(), "service.pem")
	if err := os.WriteFile(cert, public, 0600); err != nil {
		t.Fatal(err)
	}
	private, err := ecdh.X25519().GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	peerKey := base64.StdEncoding.EncodeToString(private.PublicKey().Bytes())
	first := launchConsole(t, cert)
	session := first.reply(t, "")["session"].(string)
	saved := fmt.Sprintf("admit %s laptop 10.93.0.2 %s %d", session, peerKey, freeUDP(t))
	grant := first.reply(t, saved)
	if grant["active"] != true {
		t.Fatalf("grant refused: %v", grant)
	}
	revoke := fmt.Sprintf("revoke laptop %s", grant["generation"])
	if first.reply(t, revoke)["active"] != false {
		t.Fatal("revocation failed")
	}
	first.stop(t)

	restarted := launchConsole(t, cert)
	if restarted.reply(t, "")["session"] == session {
		t.Fatal("reused session after process restart")
	}
	if restarted.reply(t, saved)["error"] == nil || restarted.reply(t, revoke)["error"] == nil || len(restarted.reply(t, "status")) != 0 {
		t.Fatal("old console input restored peer authority")
	}
	restarted.stop(t)
}
