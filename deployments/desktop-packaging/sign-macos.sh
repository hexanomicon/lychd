#!/bin/bash
# Signing is local to the release custodian's unlocked keychain.
set -euo pipefail
: "${LYCHD_APPLE_TEAM:?Set the expected Apple team ID}"
: "${LYCHD_APPLE_APPLICATION:?Set the full Developer ID Application identity}"
: "${LYCHD_APPLE_INSTALLER:?Set the full Developer ID Installer identity}"
: "${LYCHD_NOTARY_PROFILE:?Set the existing notarytool keychain profile}"
[[ "$LYCHD_APPLE_TEAM" =~ ^[A-Z0-9]{10}$ ]]
[[ "$LYCHD_APPLE_APPLICATION" == "Developer ID Application: "*" ($LYCHD_APPLE_TEAM)" ]]
[[ "$LYCHD_APPLE_INSTALLER" == "Developer ID Installer: "*" ($LYCHD_APPLE_TEAM)" ]]
case "$1" in
    runtime)
        # Visit actual Mach-O files and their enclosing bundles inside-out. Scripts and
        # symlinks have no separate code signature. Reject a failed team requirement.
        while IFS= read -r -d '' path; do
            if [[ -d "$path" ]] || [[ "$(/usr/bin/file -b "$path")" == *Mach-O* ]]; then
                /usr/bin/codesign --force --options runtime --timestamp --sign "$LYCHD_APPLE_APPLICATION" "$path"
                /usr/bin/codesign --verify --strict -R="anchor apple generic and certificate leaf[subject.OU] = \"$LYCHD_APPLE_TEAM\"" "$path"
            fi
        done < <(/usr/bin/find "$2" -depth \( -type f -o -type d \( -name '*.app' -o -name '*.framework' \) \) -print0)
        ;;
    installer)
        /usr/bin/productsign --sign "$LYCHD_APPLE_INSTALLER" --timestamp "$2" "$3"
        /usr/sbin/pkgutil --check-signature "$3" | /usr/bin/grep -F "1. $LYCHD_APPLE_INSTALLER"
        /usr/bin/xcrun notarytool submit "$3" --keychain-profile "$LYCHD_NOTARY_PROFILE" --wait
        /usr/bin/xcrun stapler staple "$3"
        /usr/bin/xcrun stapler validate "$3"
        /usr/sbin/spctl --assess --type install --verbose=4 "$3"
        ;;
    *) exit 2 ;;
esac
