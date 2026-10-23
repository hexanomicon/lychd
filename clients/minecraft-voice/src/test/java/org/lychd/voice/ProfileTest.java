package org.lychd.voice;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Pure JDK custody checks for the explicitly qualified POSIX profile, without Minecraft or sockets. */
class ProfileTest {
    @TempDir Path directory;

    @Test void absentIsInertAndPrivateRegularFileIsReadOnceAsTypedData() throws Exception {
        Path path = directory.resolve("lychd-voice.json");
        assertNull(Profile.read(path));
        Files.writeString(path, ProtocolTest.profile("http://127.0.0.1:18186"));
        Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-------"));
        assertEquals(18186, Profile.read(path).port);
        Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-r-----"));
        IllegalArgumentException refused = assertThrows(IllegalArgumentException.class, () -> Profile.read(path));
        assertFalse(refused.getMessage().contains("a".repeat(64)));
    }
    @Test void symlinkOversizeAndWritableParentNeverBecomePrivateProfiles() throws Exception {
        Path path = directory.resolve("private.json"), link = directory.resolve("lychd-voice.json");
        Files.writeString(path, ProtocolTest.profile("http://127.0.0.1:18186"));
        Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-------"));
        Files.createSymbolicLink(link, path.getFileName());
        assertThrows(IllegalArgumentException.class, () -> Profile.read(link));
        Files.delete(link);
        Files.writeString(path, "a".repeat(4097));
        assertThrows(IllegalArgumentException.class, () -> Profile.read(path));
        Files.writeString(path, ProtocolTest.profile("http://127.0.0.1:18186"));
        Files.setPosixFilePermissions(directory, PosixFilePermissions.fromString("rwxrwx---"));
        try { assertThrows(IllegalArgumentException.class, () -> Profile.read(path)); }
        finally { Files.setPosixFilePermissions(directory, PosixFilePermissions.fromString("rwx------")); }
    }
}
