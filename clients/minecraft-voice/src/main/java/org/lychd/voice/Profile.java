package org.lychd.voice;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.UserPrincipal;
import java.util.Map;
import java.util.Set;

/** Never stringify this object: it owns a private bearer credential. */
final class Profile {
    final int port;
    final String token;
    final String serverAddress;
    final String playerId;
    final int recordSeconds;

    private Profile(int port, String token, String serverAddress, String playerId, int recordSeconds) {
        this.port = port; this.token = token; this.serverAddress = serverAddress;
        this.playerId = playerId; this.recordSeconds = recordSeconds;
    }

    static Profile parse(byte[] bytes) {
        Map<String, Object> data = Json.object(bytes, 4096);
        Protocol.keys(data, "protocol", "endpoint", "token", "server_address", "player_id", "record_seconds");
        Protocol.integer(data, "protocol", 1, 1);
        String endpoint = Protocol.string(data, "endpoint");
        if (!endpoint.matches("http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}")) throw Json.invalid();
        int port;
        try { port = Integer.parseInt(endpoint.substring("http://127.0.0.1:".length())); }
        catch (NumberFormatException exception) { throw Json.invalid(); }
        if (port > 65535) throw Json.invalid();
        String token = Protocol.hex(data, "token");
        String address = Protocol.string(data, "server_address");
        if (address.isEmpty() || address.length() > 255
                || address.chars().anyMatch(ch -> ch <= 32 || ch > 126)) throw Json.invalid();
        String player = Protocol.uuid(data, "player_id");
        int duration = (int) Protocol.integer(data, "record_seconds", 1, 15);
        return new Profile(port, token, address, player, duration);
    }

    /** Missing is inert. Non-POSIX custody, symlinks and invalid contents all disable controls. */
    static Profile read(Path path) throws IOException {
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return null;
        UserPrincipal owner = path.getFileSystem().getUserPrincipalLookupService()
                .lookupPrincipalByName(System.getProperty("user.name"));
        PosixFileAttributes before = Files.readAttributes(path, PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        privateFile(before, owner);
        // A different user must not be able to replace the file between the custody checks.
        PosixFileAttributes directory = Files.readAttributes(path.getParent(), PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!directory.isDirectory() || !directory.owner().equals(owner)
                || directory.permissions().contains(PosixFilePermission.GROUP_WRITE)
                || directory.permissions().contains(PosixFilePermission.OTHERS_WRITE)) throw Json.invalid();
        Set<OpenOption> options = Set.of(StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
        ByteBuffer buffer = ByteBuffer.allocate(4097);
        try (SeekableByteChannel channel = Files.newByteChannel(path, options)) {
            while (buffer.hasRemaining() && channel.read(buffer) != -1) { /* finite file read */ }
        }
        PosixFileAttributes after = Files.readAttributes(path, PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        privateFile(after, owner);
        if (before.fileKey() == null || !before.fileKey().equals(after.fileKey())
                || !before.lastModifiedTime().equals(after.lastModifiedTime()) || before.size() != after.size()
                || buffer.position() > 4096 || buffer.position() != after.size()) throw Json.invalid();
        buffer.flip(); byte[] bytes = new byte[buffer.remaining()]; buffer.get(bytes);
        return parse(bytes);
    }

    private static void privateFile(PosixFileAttributes attributes, UserPrincipal owner) {
        if (!attributes.isRegularFile() || !attributes.owner().equals(owner) || attributes.size() > 4096
                || attributes.permissions().stream().anyMatch(permission -> permission.name().startsWith("GROUP_")
                || permission.name().startsWith("OTHERS_"))) throw Json.invalid();
    }

    @Override public String toString() { return "Private voice control profile"; }
}
