---
paths:
  - "**/*.go"
---
# Go
<!-- Clio starter — /clio-setup step 4. Verify every line against this repo, delete lines that
     don't hold here, delete the whole file if the repo has no Go. Keep it under 20 lines. -->

- `gofmt` (or `goimports`) on every file; `go vet ./...` clean; tests `go test -race ./...`.
- Generated — edit the source, run `go generate ./...`, never touch the output: `*.pb.go` (← `.proto`), `wire_gen.go` (← `wire.go`), `mock_*.go` / `*_mock.go` (← the interface, mockgen/counterfeiter), `*_string.go` (← stringer).
- Errors: return them, don't panic; wrap with `fmt.Errorf("<op>: %w", err)`; never `_ = err`.
- `context.Context` is the first parameter of anything doing I/O; never stored in a struct.
- `go.mod` + `go.sum` are the source of truth; `go mod tidy` after any dependency change, commit both.
- Build tags and `//go:embed` paths are part of the build — grep for them before moving or renaming a file.
- Money: integer minor units (`int64`) or a decimal package already in `go.mod`; never `float64`.
