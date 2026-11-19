#!/usr/bin/env bash
# Create (or update) the Spyglass conda env inside the Ubuntu-24.04 WSL2 distro, from
# spyglass-env.yaml plus the post-install pins described in that file's header.
# Miniforge is expected at /opt/miniforge3.
#
# Spyglass cannot be imported on native Windows Python (it forces the POSIX-only
# multiprocessing "fork" start method at import time), so the Spyglass side runs in
# Linux under WSL2. MySQL stays in its Docker Desktop container, reachable from WSL at
# 127.0.0.1:3306.
#
# Run inside the distro (optional argument: env name, default spyglass-gonzalez-sulser-lab-env):
#   wsl -d Ubuntu-24.04 -- bash /mnt/c/<path to repo>/src/gonzalez_sulser_lab_to_nwb/hristova_2025/spyglass/bootstrap_wsl.sh
set -euo pipefail

MINIFORGE=/opt/miniforge3
ENV_YAML="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/spyglass-env.yaml"
ENV_NAME="${1:-spyglass-gonzalez-sulser-lab-env}"
SPYGLASS="git+https://github.com/catalystneuro/spyglass.git@gonzalez-sulser-example-v1"

source "${MINIFORGE}/etc/profile.d/conda.sh"

if conda env list | grep -qE "^\s*${ENV_NAME}\s"; then
  echo "=== updating existing '${ENV_NAME}' env from ${ENV_YAML} ==="
  conda env update -n "${ENV_NAME}" -f "${ENV_YAML}" --prune
else
  echo "=== creating '${ENV_NAME}' env from ${ENV_YAML} ==="
  conda env create -n "${ENV_NAME}" -f "${ENV_YAML}"
fi

# Pins pip can't resolve together with the yaml's packages (see the yaml header).
# Each step is a separate pip call on purpose: pip reports the known conflicts as
# warnings instead of refusing to install.
PIP="conda run -n ${ENV_NAME} python -m pip"

echo "=== Spyglass at tag gonzalez-sulser-example-v1 (pip keeps an installed copy otherwise) ==="
${PIP} install --force-reinstall --no-deps "${SPYGLASS}"

echo "=== pynwb/hdmf for NWB 2.11, ndx-hed (numpy 2, so scipy>=1.13) ==="
${PIP} install "pynwb==4.2.0" "hdmf==6.2.0" "ndx-hed==0.3.0" "scipy==1.15.3"

echo "=== kachery-cloud, then re-pin pubnub for Spyglass ==="
${PIP} install kachery-cloud
${PIP} install "pubnub<6.4"

echo "=== versions ==="
conda run -n "${ENV_NAME}" python -c "import importlib.metadata as m; \
print({p: m.version(p) for p in ('spyglass-neuro','datajoint','pynwb','hdmf','numpy','scipy','ndx-hed','ndx-franklab-novela','kachery-cloud','pubnub')})"

echo "=== BOOTSTRAP DONE ==="
