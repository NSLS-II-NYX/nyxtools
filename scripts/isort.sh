#!/bin/bash

set -vxeuo pipefail

isort --line-length=115 --profile black . ${1:-}
