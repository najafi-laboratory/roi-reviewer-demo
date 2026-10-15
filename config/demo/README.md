# Demo configurations (lab-specific)

Everything in this folder describes two specific recordings from the Najafi
laboratory and exists only as a worked example of how `config/template.yaml`
gets filled in. **Nothing outside this folder depends on it.**

To start clean:

```bash
rm -rf config/demo data/demo
```

`scripts/demo_assemble_ppc_session.sh` builds the PPC session directory from
laboratory storage, where the Suite2p outputs, the inferred spikes and the
red-channel labels live in three different places. The cerebellar session needs
no assembly: it is already a complete Suite2p session directory, and its config
pins `input_layout: suite2p` because that session also carries a deprecated
`qc_results/` tree that auto-detection would otherwise select.

The datasets these configs point at are published separately; see
`scripts/fetch_demo_data.py` for the archive record and
[`../../README.md`](../../README.md) for what each one demonstrates.
