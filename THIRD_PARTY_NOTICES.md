# Third-party notices

SuperMedicine includes an integration bridge for the real OpenTUI runtime.

## @opentui/core

- Package: `@opentui/core`
- Version: `0.4.1`
- License: MIT
- Source: <https://github.com/anomalyco/opentui>
- Use: terminal UI runtime initialization, render loop, input handling, layout
  mounting and cleanup for the SuperMedicine TUI entrypoint.

The OpenTUI dependency is consumed as a package dependency. No OpenTUI source
files are vendored into this repository by this notice.

The locked OpenTUI dependency tree also installs the following non-MIT runtime
dependencies:

- Package: `diff`
- License: BSD-3-Clause
- Use: transitive dependency of `@opentui/core`.

- Package: `typescript`
- License: Apache-2.0
- Use: transitive dependency metadata present in the lockfile for
  `@opentui/core` tooling.

MIT notice for OpenTUI package use:

> MIT License
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.
