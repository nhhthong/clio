---
paths:
  - "**/*.dart"
---
# Dart / Flutter
<!-- Clio starter — /clio:setup step 4. Verify every line against this repo, delete lines that
     don't hold here, delete the whole file if the repo has no Dart. Keep it under 20 lines. -->

- Before finishing: `dart format .`, `flutter analyze` (warnings count as errors here), `flutter test`.
- Generated — edit the annotated source, run `dart run build_runner build --delete-conflicting-outputs`, never edit the output: `*.g.dart`, `*.freezed.dart`, `*.gr.dart`, `lib/gen/`.
- After any `await` inside a widget or state, check `mounted` (or `context.mounted`) before touching `BuildContext`.
- `const` constructors and widgets wherever possible; extract widgets, not helper methods that return widgets.
- State management: the package `pubspec.yaml` already lists (Riverpod / Bloc / Provider) — never introduce a second one.
- `pubspec.lock` is committed for apps; `flutter pub get` after editing `pubspec.yaml`.
- `android/`, `ios/`, `macos/`, `web/` are platform config, not Dart — say so and ask before editing them.
- "Verified" for UI work means a device or emulator run recorded in `## Testing Done`, not only `flutter test`.
