# Build the sdist the same way the release workflow does (python -m build) and install it,
# a quick way to check what a release would contain.
$ErrorActionPreference = "Stop"

if (Test-Path "./dist") { Remove-Item "./dist" -Recurse -Force }
python -m pip install --quiet --upgrade build
python -m build --sdist

pip uninstall -y django-simple-third-party-jwt
$package = Get-ChildItem ./dist -Filter "*.tar.gz" | Select-Object -First 1
python -m pip install $package.FullName
