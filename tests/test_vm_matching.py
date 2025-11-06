from pve_multiexec.api_exec_configs.router import ExecConfigResult
from pve_multiexec.api_invocations.utils import check_vm_match
from pve_multiexec.pve.schemas import PveQemuVm


def test_check_vm_match_by_tag():
    vm = PveQemuVm(vmid=101, status="running", tags="deb12;batch")
    config = ExecConfigResult(
        id=1,
        name="Batch Workers",
        include_tags=["batch"],
        exclude_tags=[],
        include_vmids=[],
        cmd_template_id=1,
    )
    assert check_vm_match(vm, config) is True


def test_check_vm_match_excluded_tag():
    vm = PveQemuVm(vmid=101, status="running", tags="deb12;batch;critical")
    config = ExecConfigResult(
        id=1,
        name="Batch Non-Critical",
        include_tags=["batch"],
        exclude_tags=["critical"],
        include_vmids=[],
        cmd_template_id=1,
    )
    assert check_vm_match(vm, config) is False


def test_check_vm_match_by_vmid():
    vm = PveQemuVm(vmid=200, status="running", tags="deb12")
    config = ExecConfigResult(
        id=1,
        name="Specific VM",
        include_tags=["dev"],
        exclude_tags=[],
        include_vmids=[200, 201],
        cmd_template_id=1,
    )
    assert check_vm_match(vm, config) is True


def test_check_vm_no_match():
    vm = PveQemuVm(vmid=300, status="running", tags="deb12")
    config = ExecConfigResult(
        id=1,
        name="Unmatched",
        include_tags=["dev"],
        exclude_tags=[],
        include_vmids=[100],
        cmd_template_id=1,
    )
    assert check_vm_match(vm, config) is False


def test_check_vm_none_tags():
    vm = PveQemuVm(vmid=400, status="running", tags=None)
    config = ExecConfigResult(
        id=1,
        name="No Tags",
        include_tags=["prod"],
        exclude_tags=[],
        include_vmids=[400],
        cmd_template_id=1,
    )
    assert check_vm_match(vm, config) is True
