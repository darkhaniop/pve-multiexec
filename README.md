# pve-drop-guest-caches

A simple utility that provides a RESTful interface for "dropping caches" in the Proxmox VE quest VMs.

## Running a Dev Server

```shell
uv run hypercorn pve_drop_guest_caches:app --bind 0.0.0.0:8081 --reload
```

## Preliminary Dependencies

* Proxmoxer
* cachetools
* FastAPI
* hypercorn
* python-dotenv
* requests (since it's one of the optional backends for Proxmoxer, we have to add it manually)

## Next Steps

Just a reminder for myself about the next steps.

Higher priority:

* Implement the invocations endpoint, this is a more generic approach compared to the previous `drop_caches`, single command.
* Implement aggregate memory consumption info endpoint.
* Sanitize the list of VMs based on running states of the VMs (not guaranteed to be accurate, because fetching VM states and posting `drop_caches` cannot be done atomically, but allow not sending requests to VMs that are known to be offline or missing).

Lower priority:

* Implement more flexible filtering methods for VM selection.
* Implement custom commands (e.g., view system info)
* **done** Run 2-3 workers, so that `drop_caches` POST requests can be sent in parallel.
* Rate-limit calls to the upstream server with `cachetools`.
* Add the CLI script
* Add CLI params to set
    * the number of workers
    * the usual host and port
    * cache TTL
    * etc.

Superseded:

* (from high-prio list) ~~Implement the `drop_caches` endpoint (accept a list of VMs).~~
* (from high-prio list) ~~Implement the `drop_caches_tagged` endpoint (accept a non-empty list of tags).~~
