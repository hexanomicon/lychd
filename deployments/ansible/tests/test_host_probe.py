"""Pure refusal oracles; never invoke provisioning or probe a target host."""

import base64
import importlib.util
import json
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import mock_open, patch

PROBE = Path(__file__).parents[1] / "roles/tumbleweed_host/files/host_probe.py"
SPEC = importlib.util.spec_from_file_location("host_probe", PROBE)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def fixture_intent():
    raw = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes(range(32))
    return {
        "name": "lychd",
        "uid": 1001,
        "gid": 1001,
        "subuid_start": 231072,
        "subgid_start": 231072,
        "count": 65536,
        "keys": ["ssh-ed25519 " + base64.b64encode(raw).decode()],
    }


def mounts():
    text = "\n".join(
        f"{i} 0 0:41 /@{suffix} {path} rw - btrfs /dev/vda2 rw"
        for i, (suffix, path) in enumerate((("", "/"), ("/home", "/home"), ("/var", "/var")), 20)
    )
    return probe.parse_mounts(text)


class IntentTests(unittest.TestCase):
    def test_valid_plain_public_key(self):
        self.assertEqual(probe.validate_intent(fixture_intent())["uid"], 1001)

    def test_empty_keys_fail_before_observation(self):
        value = fixture_intent()
        value["keys"] = []
        with self.assertRaisesRegex(probe.Refusal, "supply"):
            probe.validate_intent(value)

    def test_no_boolean_ids_or_variable_commands(self):
        for key, invalid in (("uid", True), ("subuid_start", "1; id"), ("name", "root"), ("count", 1)):
            value = fixture_intent()
            value[key] = invalid
            with self.subTest(key=key), self.assertRaises(probe.Refusal):
                probe.validate_intent(value)

    def test_reject_options_private_key_and_duplicate_identity(self):
        for keys in (
            ["command=whoami " + fixture_intent()["keys"][0]],
            ["-----BEGIN OPENSSH PRIVATE KEY-----"],
            fixture_intent()["keys"] * 2,
        ):
            value = fixture_intent()
            value["keys"] = keys
            with self.assertRaises(probe.Refusal):
                probe.validate_intent(value)

    def test_reject_bad_public_key_payload(self):
        value = fixture_intent()
        value["keys"] = ["ssh-ed25519 " + base64.b64encode(struct.pack(">I", 11) + b"ssh-ed25519").decode()]
        with self.assertRaisesRegex(probe.Refusal, "ssh-keygen"):
            probe.validate_intent(value)


class DelegationTests(unittest.TestCase):
    def manager(self, running=True):
        return {
            "NeedDaemonReload": "no",
            "Slice": "user-1001.slice",
            "ControlGroup": "/user.slice/user-1001.slice/user@1001.service" if running else "",
            "Delegate": "yes",
            "DelegateControllers": "cpu memory pids",
        }

    def properties(self, unit, *names):
        return (
            self.manager()
            if unit.startswith("user@")
            else {
                "NeedDaemonReload": "no",
                "Slice": {"-.slice": "", "user.slice": "-.slice", "user-1001.slice": "user.slice"}[unit],
            }
        )

    def test_cgroup_boundary_cannot_escape_or_use_noncanonical_paths(self):
        for value in (
            "",
            "/",
            "relative",
            "//elsewhere",
            "/user.slice/../elsewhere",
            "/user.slice//child",
            "/user.slice/",
            "/bad\n",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(probe.Refusal, "ControlGroup"):
                probe.delegation_boundary(value)
        self.assertEqual(
            probe.delegation_boundary("/user.slice/user-1001.slice/user@1001.service"),
            Path("/sys/fs/cgroup/user.slice/user-1001.slice/user@1001.service"),
        )

    def test_verifier_checks_available_controllers_not_idle_subtree_enablement(self):
        with (
            patch.object(probe, "trusted_delegation_path", return_value=True),
            patch.object(probe, "unit_properties", side_effect=self.properties),
            patch.object(probe, "require_no_local_controller_policy"),
            patch.object(probe.Path, "resolve", autospec=True, side_effect=lambda path, **kw: path),
            patch.object(probe.Path, "read_text", return_value="cpu memory pids") as read,
            patch.object(probe, "command") as commands,
        ):
            probe.observe_delegation(1001, True, True)
            self.assertEqual(read.call_count, 2)
            commands.assert_not_called()

    def test_empty_delegation_is_not_cpu_memory_authority(self):
        for delegated, available in (("", "cpu memory pids"), ("cpu memory pids", "pids")):
            with self.subTest(delegated=delegated, available=available):
                with self.assertRaisesRegex(probe.Refusal, "activation pending"):
                    probe.validate_live_delegation({"Delegate": "yes", "DelegateControllers": delegated}, available)
        probe.validate_live_delegation(
            {"Delegate": "yes", "DelegateControllers": "pids cpu memory"}, "cpu memory pids io"
        )

    def test_safe_absent_destination_and_unsafe_ancestor(self):
        path = probe.delegation_path(1001)
        with patch.object(probe.os.path, "lexists", side_effect=lambda p: p != path):
            with patch.object(probe.Path, "lstat", return_value=SimpleNamespace(st_mode=0o40755, st_uid=0)):
                self.assertFalse(probe.trusted_delegation_path(path))
            for mode, uid in ((0o120777, 0), (0o40777, 0), (0o40755, 1001)):
                with patch.object(probe.Path, "lstat", return_value=SimpleNamespace(st_mode=mode, st_uid=uid)):
                    with self.assertRaisesRegex(probe.Refusal, "unsafe delegation directory"):
                        probe.trusted_delegation_path(path)

    def test_reserved_file_links_modes_owner_and_content(self):
        path = probe.delegation_path(1001)
        directory = SimpleNamespace(st_mode=0o40755, st_uid=0)
        regular = dict(st_mode=0o100644, st_uid=0, st_nlink=1, st_dev=1, st_ino=2)
        for change in ({"st_mode": 0o120777}, {"st_nlink": 2}, {"st_uid": 1001}, {"st_mode": 0o100666}):
            value = SimpleNamespace(**(regular | change))
            with (
                patch.object(probe.os.path, "lexists", return_value=True),
                patch.object(
                    probe.Path, "lstat", autospec=True, side_effect=lambda p: value if p == path else directory
                ),
                self.assertRaisesRegex(probe.Refusal, "unsafe delegation file"),
            ):
                probe.trusted_delegation_path(path)
        for content in (probe.DELEGATION_CONTENT, "[Service]\nDelegate=yes\n"):
            with (
                patch.object(probe.os.path, "lexists", return_value=True),
                patch.object(
                    probe.Path,
                    "lstat",
                    autospec=True,
                    side_effect=lambda p: SimpleNamespace(**regular) if p == path else directory,
                ),
                patch.object(probe.os, "open", return_value=3) as opened,
                patch.object(probe.os, "fstat", return_value=SimpleNamespace(**regular)),
                patch.object(probe.os, "fdopen", mock_open(read_data=content)),
            ):
                if content == probe.DELEGATION_CONTENT:
                    self.assertTrue(probe.trusted_delegation_path(path))
                else:
                    with self.assertRaisesRegex(probe.Refusal, "foreign delegation"):
                        probe.trusted_delegation_path(path)
                self.assertTrue(opened.call_args.args[1] & probe.os.O_NOFOLLOW)

    def test_local_conflicts_and_ancestor_disabling_refuse(self):
        owned = probe.delegation_path(1001)
        with self.assertRaisesRegex(probe.Refusal, "disabled"):
            probe.require_no_local_controller_policy("user.slice", {"DisableControllers": "memory"}, owned)
        with (
            patch.object(probe, "trusted_file", return_value=True),
            patch.object(probe.Path, "read_text", return_value="[Service]\nDelegate=\n"),
            self.assertRaisesRegex(probe.Refusal, "local controller policy"),
        ):
            probe.require_no_local_controller_policy("user@1001.service", {"DropInPaths": "/etc/foreign.conf"}, owned)
        probe.require_no_local_controller_policy(
            "user@1001.service", {"DropInPaths": "/usr/lib/systemd/system/user@.service.d/20-defaults-SUSE.conf"}, owned
        )

    def test_usr_local_manager_fragments_and_controller_dropins_are_local_policy(self):
        owned = probe.delegation_path(1001)
        with self.assertRaisesRegex(probe.Refusal, "local user-manager unit override"):
            probe.require_no_local_controller_policy(
                "user@1001.service", {"FragmentPath": "/usr/local/lib/systemd/system/user@.service"}, owned
            )
        for unit, directive in (("user@1001.service", "Delegate="), ("user.slice", "DisableControllers=memory")):
            with (
                patch.object(probe, "trusted_file", return_value=True),
                patch.object(probe.Path, "read_text", return_value=directive),
                self.assertRaisesRegex(probe.Refusal, "local controller policy"),
            ):
                probe.require_no_local_controller_policy(
                    unit, {"DropInPaths": f"/usr/local/lib/systemd/system/{unit}.d/90-local.conf"}, owned
                )

    def test_stale_or_unknown_cached_policy_refuses_preflight_and_verification_without_reload(self):
        for stale_unit in ("user@1001.service", "-.slice", "user.slice", "user-1001.slice"):
            for freshness in ("yes", "", None):
                for verify in (False, True):

                    def properties(unit, *names):
                        self.assertIn("NeedDaemonReload", names)
                        result = self.properties(unit)
                        if unit == stale_unit:
                            result["NeedDaemonReload"] = freshness
                            # Cached paths can omit an administrator's unreloaded drop-in.
                            result["DropInPaths"] = ""
                        return result

                    with (
                        self.subTest(unit=stale_unit, freshness=freshness, verify=verify),
                        patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
                        patch.object(probe, "trusted_delegation_path", return_value=verify),
                        patch.object(probe, "unit_properties", side_effect=properties),
                        patch.object(probe, "command") as commands,
                        self.assertRaisesRegex(probe.Refusal, "stale or unknown systemd unit policy"),
                    ):
                        probe.observe_delegation(1001, verify, verify)
                    commands.assert_not_called()

    def test_existing_missing_artifact_requires_maintenance_without_bus_or_podman(self):
        for stage in ("maps_initialized", "configured"):
            receipt = ReceiptTests().receipt(stage)
            self.assertEqual(
                probe.validate_receipt(receipt, fixture_intent(), True, True, {"uid": True, "gid": True}, False),
                stage,
            )
            for verify in (False, True):
                with (
                    patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
                    patch.object(probe, "trusted_delegation_path", return_value=False),
                    patch.object(probe, "command") as commands,
                    self.assertRaisesRegex(probe.Refusal, "operator preparation.*receipt remains valid"),
                ):
                    probe.observe_delegation(1001, True, verify)
                commands.assert_not_called()

    def test_valid_postmap_identity_with_artifact_resumes_without_user_bus_or_podman(self):
        receipt = ReceiptTests().receipt("maps_initialized")
        self.assertEqual(
            probe.validate_receipt(receipt, fixture_intent(), True, True, {"uid": True, "gid": True}, False),
            "maps_initialized",
        )
        for running in (False, True):

            def properties(unit, *names):
                return self.manager(running) if unit.startswith("user@") else self.properties(unit)

            with (
                patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
                patch.object(probe, "trusted_delegation_path", return_value=True),
                patch.object(probe, "unit_properties", side_effect=properties),
                patch.object(probe, "require_no_local_controller_policy"),
                patch.object(probe, "command") as commands,
            ):
                self.assertTrue(probe.observe_delegation(1001, True, False)["present"])
            commands.assert_not_called()

    def test_custom_slice_and_canonical_but_foreign_cgroup_refuse(self):
        for change in ({"Slice": "custom.slice"}, {"ControlGroup": "/custom.slice/user@1001.service"}):
            with (
                patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
                patch.object(probe, "trusted_delegation_path", return_value=True),
                patch.object(probe, "unit_properties", return_value=self.manager() | change),
                self.assertRaisesRegex(probe.Refusal, "custom user-manager placement"),
            ):
                probe.observe_delegation(1001, True, True)

        def custom_ancestor(unit, *names):
            return self.properties(unit) | ({"Slice": "custom.slice"} if unit == "user.slice" else {})

        with (
            patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
            patch.object(probe, "trusted_delegation_path", return_value=True),
            patch.object(probe, "unit_properties", side_effect=custom_ancestor),
            patch.object(probe, "require_no_local_controller_policy"),
            self.assertRaisesRegex(probe.Refusal, "custom ancestor placement"),
        ):
            probe.observe_delegation(1001, True, True)

    def test_new_identity_may_plan_missing_artifact(self):
        with (
            patch.object(probe.Path, "read_text", return_value="cpu memory pids"),
            patch.object(probe, "trusted_delegation_path", return_value=False),
            patch.object(probe, "unit_properties", side_effect=self.properties),
            patch.object(probe, "require_no_local_controller_policy"),
        ):
            self.assertFalse(probe.observe_delegation(1001, False, False)["present"])


class AllocationTests(unittest.TestCase):
    def check(self, text, real_ids=None):
        return probe.validate_ranges(text, "lychd", 1001, 231072, 65536, real_ids or {0, 1000, 1001})

    def test_first_run_and_exact_idempotent_mapping(self):
        self.assertFalse(self.check("alice:100000:65536\n"))
        self.assertTrue(self.check("alice:100000:65536\nlychd:231072:65536\n"))

    def test_no_remapping_multiple_own_maps_or_numeric_alias(self):
        for text in ("lychd:300000:65536", "lychd:231072:65536\nlychd:400000:65536", "1001:231072:65536"):
            with self.subTest(text=text), self.assertRaisesRegex(probe.Refusal, "never remap"):
                self.check(text)

    def test_refuse_existing_collisions_and_real_id_coverage(self):
        for text in ("alice:220000:65536", "a:100000:65536\nb:120000:65536", "a:1:65536", "malformed"):
            with self.subTest(text=text), self.assertRaises(probe.Refusal):
                self.check(text)
        with self.assertRaisesRegex(probe.Refusal, "real host ID"):
            self.check("", {250000})

    def test_adjacent_ranges_do_not_overlap(self):
        self.assertFalse(self.check("alice:165536:65536\nbob:296608:65536"))


class ReceiptTests(unittest.TestCase):
    def receipt(self, stage):
        return {
            "schema_version": 1,
            "stage": stage,
            "identity": {k: v for k, v in fixture_intent().items() if k != "keys"},
        }

    def test_fresh_identity_has_no_existing_authority(self):
        self.assertEqual(
            probe.validate_receipt(None, fixture_intent(), False, False, {"uid": False, "gid": False}, False), "absent"
        )
        for account, group, maps, linger in (
            (True, False, {"uid": False, "gid": False}, False),
            (False, True, {"uid": False, "gid": False}, False),
            (False, False, {"uid": True, "gid": False}, False),
            (False, False, {"uid": False, "gid": False}, True),
        ):
            with self.subTest(state=(account, group, maps, linger)), self.assertRaisesRegex(probe.Refusal, "adoption"):
                probe.validate_receipt(None, fixture_intent(), account, group, maps, linger)

    def test_interrupted_pre_map_creation_always_needs_manual_recovery(self):
        # No inferred safety from missing keys, linger, process lists or storage paths.
        for account in (False, True):
            for maps in ({"uid": False, "gid": False}, {"uid": True, "gid": True}):
                with self.subTest(account=account, maps=maps), self.assertRaisesRegex(probe.Refusal, "manual recovery"):
                    probe.validate_receipt(self.receipt("creating"), fixture_intent(), account, True, maps, False)

    def test_initialized_and_configured_missing_maps_refused_even_for_external_graphroot(self):
        # The decision has no graphroot input: default and custom stores cannot bypass it.
        for stage in ("maps_initialized", "configured"):
            for maps in ({"uid": False, "gid": False}, {"uid": True, "gid": False}, {"uid": False, "gid": True}):
                with (
                    self.subTest(stage=stage, maps=maps),
                    self.assertRaisesRegex(probe.Refusal, "regardless of container storage path"),
                ):
                    probe.validate_receipt(self.receipt(stage), fixture_intent(), True, True, maps, True)

    def test_post_map_interruption_can_resume_only_with_exact_retained_identity_and_maps(self):
        for stage in ("maps_initialized", "configured"):
            self.assertEqual(
                probe.validate_receipt(
                    self.receipt(stage), fixture_intent(), True, True, {"uid": True, "gid": True}, False
                ),
                stage,
            )
            with self.assertRaises(probe.Refusal):
                probe.validate_receipt(
                    self.receipt(stage), fixture_intent(), False, True, {"uid": True, "gid": True}, False
                )

    def test_legacy_receipt_and_changed_identity_never_license_remapping(self):
        legacy = {k: v for k, v in fixture_intent().items() if k != "keys"}
        changed = self.receipt("configured")
        changed["identity"]["uid"] += 1
        for value in (legacy, changed):
            with self.subTest(value=value), self.assertRaises(probe.Refusal):
                probe.validate_receipt(value, fixture_intent(), True, True, {"uid": True, "gid": True}, True)


class AuthorityTests(unittest.TestCase):
    def test_home_parent_must_not_allow_runtime_replacement(self):
        probe.validate_mount_parent(SimpleNamespace(st_mode=0o40755, st_uid=0))
        for mode, uid in ((0o40777, 0), (0o40775, 0), (0o40755, 1001), (0o100644, 0)):
            with self.subTest(mode=mode, uid=uid), self.assertRaises(probe.Refusal):
                probe.validate_mount_parent(SimpleNamespace(st_mode=mode, st_uid=uid))

    def test_new_identity_gate_checks_effective_sudo_policy(self):
        account = SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_dir="/home/lychd", pw_shell="/bin/bash")
        group = SimpleNamespace(gr_gid=1001, gr_mem=[])
        with (
            patch.object(probe.os, "geteuid", return_value=0),
            patch.dict(probe.os.environ, {"SUDO_USER": "admin"}),
            patch.object(probe.pwd, "getpwnam", return_value=account),
            patch.object(probe.grp, "getgrnam", return_value=group),
            patch.object(probe.grp, "getgrall", return_value=[group]),
            patch.object(probe, "require_no_sudo", side_effect=probe.Refusal("runtime sudo grants")) as policy,
        ):
            with self.assertRaisesRegex(probe.Refusal, "runtime sudo"):
                probe.observe_identity(fixture_intent())
            policy.assert_called_once_with()


class SudoPolicyTests(unittest.TestCase):
    # The converter expands User_Alias OPS = %operators into this Unix-group list.
    grant = {
        "User_Specs": [
            {
                "User_List": [{"usergroup": "operators"}],
                "Host_List": [{"hostname": "ALL"}],
                "Cmnd_Specs": [{"Commands": [{"command": "/usr/bin/id"}]}],
            }
        ],
    }

    def check(
        self,
        *,
        matched=None,
        complete=None,
        failure=None,
        config="",
        nss="sudoers: files\n",
        policy=None,
        changed=False,
    ):
        if policy is None:
            policy = "User_Alias OPS = %operators\nOPS ALL=(ALL) /usr/bin/id\n"
        files = {
            "/etc/sudoers": ("policy", policy),
            "/etc/sudo.conf": ("config", config),
            "/etc/nsswitch.conf": ("nss", nss),
        }

        def run(argv, **kwargs):
            self.assertEqual(kwargs["env"], {"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"})
            if failure and failure[0] in argv[0]:
                return SimpleNamespace(returncode=failure[1], stdout=failure[2], stderr=failure[3])
            if argv[0] == "/usr/bin/rpm":
                return SimpleNamespace(returncode=0, stdout="sudo\nopenSUSE\nsudo-1.9.99-1.1.src.rpm\n", stderr="")
            if argv[0] == "/usr/bin/sudo":
                self.assertEqual(argv[1:], ["-V"])
                return SimpleNamespace(returncode=0, stdout="Sudoers path: /etc/sudoers:/usr/etc/sudoers\n", stderr="")
            if argv[0].endswith("visudo"):
                self.assertEqual(argv[1:], ["-c", "-q", "-s", "-f", "/etc/sudoers"])
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            self.assertEqual(argv[:6], ["/usr/bin/cvtsudoers", "-c", "/dev/null", "-f", "json", "-e"])
            self.assertEqual(argv[-1], "/etc/sudoers")
            if "-m" in argv:
                self.assertEqual(argv[6:-1], ["-m", "user=lychd", "-M"])
                result = matched if matched is not None else {}
                if changed:
                    files["/etc/sudoers"] = ("changed", policy)
            else:
                result = complete if complete is not None else self.grant
            return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr="")

        with (
            patch.object(
                probe.shutil,
                "which",
                side_effect=lambda name, **kw: "/usr/sbin/visudo" if name == "visudo" else "/usr/bin/" + name,
            ),
            patch.object(probe, "trusted_sudo_path", return_value=SimpleNamespace(st_mode=0o100755)),
            patch.object(probe, "read_sudo_file", side_effect=lambda path, **kw: files.get(str(path))),
            patch.object(probe.pwd, "getpwnam", return_value=SimpleNamespace(pw_gid=1001)),
            patch.object(probe.os, "getgrouplist", return_value=[1001, 2000]),
            patch.object(probe.subprocess, "run", side_effect=run) as commands,
        ):
            probe.require_no_sudo()
        self.assertEqual(commands.call_count, 7)

    def test_unmatched_policy_accepts_only_after_both_conversions_and_visudo(self):
        self.check()
        self.check(matched={"User_Specs": []})

    def test_alias_expanded_local_group_grant_refuses_even_without_user_name(self):
        with self.assertRaisesRegex(probe.Refusal, "runtime sudo policy matches"):
            self.check(matched=self.grant)

    def test_parser_failures_are_not_policy_denial(self):
        for failure in (
            ("visudo", 1, "", ""),
            ("cvtsudoers", 1, "{}", ""),
            ("cvtsudoers", 0, "{}", "warning"),
            ("cvtsudoers", 0, "not json", ""),
            ("rpm", 0, "sudo 99.0\n", ""),
            ("/sudo", 0, "Sudoers path: /elsewhere\n", ""),
        ):
            with self.subTest(failure=failure), self.assertRaises(probe.Refusal):
                self.check(failure=failure)

    def test_external_constructs_cannot_disappear_in_the_user_filter(self):
        for key in ("netgroup", "nonunixgroup", "nonunixgid", "group_plugin"):
            full = {"Defaults": [{"Options": [{key: "external"}]}]}
            with self.subTest(key=key), self.assertRaisesRegex(probe.Refusal, "external sudo"):
                self.check(complete=full, matched={})

    def test_unknown_or_remote_nss_and_custom_plugins_refuse(self):
        for nss in ("sudoers: sss", "sudoers: files ldap", "sudoers: files\nsudoers: files", "sudoers: unknown"):
            with self.subTest(nss=nss), self.assertRaisesRegex(probe.Refusal, "NSS"):
                self.check(nss=nss)
        for config in (
            "Plugin custom_policy custom.so",
            "Plugin sudoers_policy /custom/sudoers.so",
            "Plugin sudoers_policy sudoers.so sudoers_file=/elsewhere",
            "Path plugin_dir /elsewhere",
            "Plugin sudoers_audit sudoers.so sudoers_file=/elsewhere",
            "Set group_source static",
        ):
            with self.subTest(config=config), self.assertRaisesRegex(probe.Refusal, "sudo.conf"):
                self.check(config=config)
        self.check(config="Plugin sudoers_policy sudoers.so\nPlugin sudoers_audit sudoers.so\n")

    def test_include_introducers_refuse_without_interpreting_paths(self):
        for directive in ("@include /elsewhere", "#include /elsewhere", "#includedir /etc/sudoers.d"):
            with self.subTest(directive=directive), self.assertRaisesRegex(probe.Refusal, "includes"):
                self.check(policy=directive)

    def test_policy_mutation_during_conversion_invalidates_the_empty_match(self):
        with self.assertRaisesRegex(probe.Refusal, "changed during observation"):
            self.check(changed=True)

    def test_missing_structured_policy_tool_never_skips_the_check(self):
        with (
            patch.object(probe.shutil, "which", return_value=None),
            patch.object(probe.subprocess, "run") as commands,
            self.assertRaisesRegex(probe.Refusal, "required for the local policy proof"),
        ):
            probe.require_no_sudo()
        commands.assert_not_called()

    def test_malformed_and_unknown_json_shapes_refuse(self):
        for text in ("not json", "[]", '{"User_Specs":{}}', '{"unexpected": []}', '{"User_Specs":[],"User_Specs":[]}'):
            with self.subTest(text=text), self.assertRaises(probe.Refusal):
                probe.sudo_json(text)
        self.assertEqual(probe.sudo_json(""), {})

    def test_unknown_user_selector_cannot_be_pruned_into_an_empty_match(self):
        full = {"User_Specs": [self.grant["User_Specs"][0] | {"User_List": [{"future_group": "remote"}]}]}
        with self.assertRaisesRegex(probe.Refusal, "member type"):
            self.check(complete=full)

    def test_policy_files_refuse_symlinks_foreign_owner_and_writable_modes(self):
        path = Path("/etc/sudoers")
        directory = SimpleNamespace(st_mode=0o40755, st_uid=0)
        for mode, uid in ((0o120777, 0), (0o100440, 1001), (0o100460, 0), (0o100442, 0)):
            file = SimpleNamespace(st_mode=mode, st_uid=uid)
            with (
                self.subTest(mode=mode, uid=uid),
                patch.object(probe.os.path, "lexists", return_value=True),
                patch.object(
                    probe.Path, "lstat", autospec=True, side_effect=lambda p: file if p == path else directory
                ),
                patch.object(probe.os, "open") as opened,
                self.assertRaisesRegex(probe.Refusal, "untrusted sudo policy input"),
            ):
                probe.read_sudo_file(path)
            opened.assert_not_called()

    def test_file_pin_uses_no_follow_and_detects_replacement(self):
        path = Path("/etc/sudoers")
        directory = SimpleNamespace(st_mode=0o40755, st_uid=0)
        fields = dict(
            st_dev=1,
            st_ino=2,
            st_mode=0o100440,
            st_uid=0,
            st_gid=0,
            st_nlink=1,
            st_size=15,
            st_mtime_ns=1,
            st_ctime_ns=1,
        )
        for replaced in (False, True):
            actual = SimpleNamespace(**(fields | ({"st_ino": 3} if replaced else {})))
            with (
                self.subTest(replaced=replaced),
                patch.object(probe.os.path, "lexists", return_value=True),
                patch.object(
                    probe.Path,
                    "lstat",
                    autospec=True,
                    side_effect=lambda p: SimpleNamespace(**fields) if p == path else directory,
                ),
                patch.object(probe.os, "open", return_value=3) as opened,
                patch.object(probe.os, "fstat", return_value=actual),
                patch.object(probe.os, "fdopen", mock_open(read_data="root ALL=ALL\n")),
            ):
                if replaced:
                    with self.assertRaisesRegex(probe.Refusal, "changed while opening"):
                        probe.read_sudo_file(path)
                else:
                    self.assertEqual(probe.read_sudo_file(path)[1], "root ALL=ALL\n")
                self.assertTrue(opened.call_args.args[1] & probe.os.O_NOFOLLOW)


class NsswitchTests(unittest.TestCase):
    def check(self, *, override_exists, contents, trusted=True):
        selected = "/etc/nsswitch.conf" if override_exists else "/usr/etc/nsswitch.conf"

        with (
            patch.object(
                probe.os.path,
                "lexists",
                return_value=override_exists,
            ),
            patch.object(
                probe,
                "trusted_file",
                side_effect=(None if trusted else probe.Refusal("untrusted NSS file")),
            ) as trust,
            patch.object(
                probe.Path,
                "read_text",
                return_value=contents,
            ) as read,
        ):
            if trusted:
                probe.validate_nsswitch()
                trust.assert_called_once_with(probe.Path(selected), optional=False)
                read.assert_called_once()
            else:
                with self.assertRaises(probe.Refusal):
                    probe.validate_nsswitch()
                read.assert_not_called()

    def test_vendor_default_when_override_absent(self):
        self.check(
            override_exists=False,
            contents="passwd: compat systemd\ngroup: compat systemd\n",
        )

    def test_etc_override_takes_precedence(self):
        self.check(
            override_exists=True,
            contents="subid: files\n",
        )

    def test_untrusted_override_is_refused(self):
        self.check(
            override_exists=True,
            contents="subid: files\n",
            trusted=False,
        )

    def test_nonlocal_subid_source_is_refused(self):
        for source in ("ldap", "sss", "files ldap"):
            with self.subTest(source=source):
                with (
                    patch.object(
                        probe.os.path,
                        "lexists",
                        return_value=False,
                    ),
                    patch.object(probe, "trusted_file"),
                    patch.object(
                        probe.Path,
                        "read_text",
                        return_value=f"subid: {source}\n",
                    ),
                ):
                    with self.assertRaisesRegex(probe.Refusal, "subid delegation"):
                        probe.validate_nsswitch()


class MountTests(unittest.TestCase):
    def test_distinct_mounted_subvolumes_on_one_filesystem(self):
        with patch.object(
            probe.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout="6e79539e-4cbf-4a44-b0ac-5a83d1fffd4d",
            ),
        ):
            probe.validate_mounts(mounts(), {"/": 256, "/home": 256, "/var": 256})

    def test_reject_parent_mount_bind_dir_second_filesystem_readonly_and_duplicate_root(self):
        for change in ("missing", "bind", "readonly", "root"):
            value, inodes = mounts(), {"/": 256, "/home": 256, "/var": 256}
            if change == "missing":
                del value["/var"]
            elif change == "bind":
                inodes["/home"] = 4242
            elif change == "readonly":
                value["/"]["options"] = ["ro"]
            else:
                value["/home"]["root"] = value["/"]["root"]
            with self.subTest(change=change), self.assertRaises(probe.Refusal):
                probe.validate_mounts(value, inodes)

    def test_btrfs_virtual_device_ids_may_differ(self):
        value = mounts()
        value["/"]["device"] = "0:40"
        value["/home"]["device"] = "0:47"
        value["/var"]["device"] = "0:53"
        with patch.object(
            probe.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout="6e79539e-4cbf-4a44-b0ac-5a83d1fffd4d\n",
            ),
        ):
            probe.validate_mounts(value, {"/": 256, "/home": 256, "/var": 256})

    def test_reject_different_btrfs_filesystems(self):
        uuids = iter(
            [
                "6e79539e-4cbf-4a44-b0ac-5a83d1fffd4d\n",
                "6e79539e-4cbf-4a44-b0ac-5a83d1fffd4d\n",
                "11111111-2222-3333-4444-555555555555\n",
            ]
        )

        def fake_run(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout=next(uuids))

        with patch.object(probe.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(probe.Refusal, "one existing Btrfs filesystem"):
                probe.validate_mounts(mounts(), {"/": 256, "/home": 256, "/var": 256})

    def test_version_comparison_is_numeric(self):
        for text, expected in (("podman version 5.4.0", True), ("5.10.1", True), ("5.3.9", False), ("invalid", False)):
            self.assertEqual(probe.version_at_least_54(text), expected)


class CliTests(unittest.TestCase):
    def test_malformed_intent_fails_without_host_probe(self):
        with (
            patch("sys.stdin", __import__("io").StringIO("{}")),
            patch("sys.argv", ["host_probe.py", "preflight"]),
            patch.object(probe, "observe") as observe,
            patch("sys.stderr", __import__("io").StringIO()),
        ):
            self.assertEqual(probe.main(), 2)
            observe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
