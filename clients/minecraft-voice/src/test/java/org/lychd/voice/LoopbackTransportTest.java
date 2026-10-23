package org.lychd.voice;

import java.io.IOException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LoopbackTransportTest {
    private String response(String headers, String body) {
        return "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n" + headers + "\r\n" + body;
    }
    @Test void exactFramingRejectsSmugglingCompressionOversizeAndTrailingBytes() throws Exception {
        String valid = response("Content-Length: 2\r\n", "{}");
        assertArrayEquals(ProtocolTest.bytes("{}"), LoopbackTransport.parseResponse(ProtocolTest.bytes(valid)).body());
        for (String invalid : new String[] {
                response("Content-Length: 2\r\nContent-Length: 2\r\n", "{}"),
                response("Content-Length: 2\r\nTransfer-Encoding: chunked\r\n", "{}"),
                response("Content-Length: 2\r\nContent-Encoding: gzip\r\n", "{}"),
                response("Content-Length: 1\r\n", "{}"), valid + "{}",
                response("Content-Length: 2\r\nX-Padding: " + "a".repeat(4096) + "\r\n", "{}"),
                valid.replace("HTTP/1.1", "HTTP/1.0"), valid.replace("Connection: close", "Connection: keep-alive"),
                response("Content-Length: 9000\r\n", "a".repeat(9000))}) {
            assertThrows(IOException.class, () -> LoopbackTransport.parseResponse(ProtocolTest.bytes(invalid)));
        }
    }
}
