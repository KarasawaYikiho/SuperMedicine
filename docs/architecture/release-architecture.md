# Release Architecture

## Source and Python distributions

`pyproject.toml` is the package-version authority. The release gate builds Wheel
and sdist, then installs the Wheel in a clean target before import and CLI smoke
checks.

## Windows artifacts

Windows packaging produces `SuperMedicine.exe`, `SuperMedicineGUI.exe`,
`SuperMedicineInstaller.exe`, `SuperMedicine.Beta{version}.zip`, and SHA-256
checksums. Each executable runs its dry-run or self-test before the archive is
accepted. The Release ZIP keeps its established root layout and includes the
installer package needed by the thin source entrypoints.

## Publication

Tag, package version, and build commit identity are verified before expensive
work. An existing version is never overwritten. Publication consumes the exact
artifact verified by the preceding job, creates a draft Release, uploads and
checks every asset, and only then makes the Release public.

Build jobs have read-only repository permission. Only the final publication job
may receive `contents: write`.
