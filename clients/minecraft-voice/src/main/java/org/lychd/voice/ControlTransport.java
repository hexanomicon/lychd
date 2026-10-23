package org.lychd.voice;

import java.io.IOException;

interface ControlTransport extends AutoCloseable {
    record Response(int status, byte[] body) { }
    Response request(String method, String path, byte[] body) throws IOException;
    @Override void close();
}
