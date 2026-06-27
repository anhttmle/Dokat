# Flutter Migration — Tasks

## Phase 0 — Prep

- [x] T0.1: Tạo `specs/flutter-migration/` (requirements, design, tasks,
      decision_log)
- [x] T0.2: Đổi tên `client/` → `client-rn/`
- [x] T0.3: Cập nhật `AGENT.md`, `ONBOARDING.md`, `.gitignore`, `PRD.md`

## Phase 1 — Scaffold Flutter Project

- [x] T1.1: Tạo Flutter project tại `client/` (tay nếu flutter CLI chưa có)
      với `pubspec.yaml`, `analysis_options.yaml`, folder structure
- [x] T1.2: Setup `core/`: `api_client.dart`, `constants.dart`
- [x] T1.3: Setup `app.dart` với `go_router` + bottom navigation shell
- [x] T1.4: Setup `main.dart` với Firebase init + ProviderScope

## Phase 2 — F01 Auth

- [x] T2.1: `features/auth/data/auth_service.dart`
- [x] T2.2: `features/auth/domain/auth_state.dart`
- [x] T2.3: `features/auth/presentation/providers/auth_notifier.dart`
- [x] T2.4: `features/auth/presentation/widgets/auth_guard.dart`
- [x] T2.5: `features/auth/presentation/widgets/link_account_sheet.dart`
- [x] T2.6: `features/auth/presentation/screens/force_link_screen.dart`
- [x] T2.7: Tests cho AuthService + AuthNotifier

## Phase 3 — F02 Profile

- [x] T3.1: Domain models: `owner_profile.dart`, `pet_profile.dart`
- [x] T3.2: `features/profile/data/profile_service.dart`
- [x] T3.3: `features/profile/data/pet_service.dart`
- [x] T3.4: Providers: `profile_notifier.dart`, `pet_notifier.dart`
- [x] T3.5: Screens: `profile_screen.dart`, `pet_timeline_screen.dart`
- [x] T3.6: Widgets: bottom sheets (create/edit pet, edit owner)
- [x] T3.7: Tests

## Phase 4 — F03 Social Graph

- [x] T4.1: Domain: `friend.dart`
- [x] T4.2: `social_service.dart`
- [x] T4.3: `friend_notifier.dart`
- [x] T4.4: `friend_list_screen.dart`, `add_friend_screen.dart`
- [x] T4.5: `qr_scanner_screen.dart` (mobile_scanner)
- [x] T4.6: `remove_friend_dialog.dart`
- [x] T4.7: Tests

## Phase 5 — F04 Capture + F05 Send

- [x] T5.1: `capture_service.dart`, `image_compressor.dart`
- [x] T5.2: `pet_validation_service.dart` (tflite_flutter)
- [x] T5.3: `camera_screen.dart` (camera package)
- [x] T5.4: Widgets: `pet_picker_overlay.dart`, `pet_selector_chip.dart`
- [x] T5.5: `send_service.dart`
- [x] T5.6: `recipient_selector_screen.dart`
- [x] T5.7: Tests

## Phase 6 — F06 Feed + F07 Seen By + F08 History

- [x] T6.1: Domain: `post.dart`
- [x] T6.2: `feed_service.dart`, `seen_service.dart`, `history_service.dart`
- [x] T6.3: `feed_screen.dart`, `feed_item.dart`
- [x] T6.4: `seen_by_list.dart`
- [x] T6.5: `history_screen.dart`, `history_list.dart`
- [x] T6.6: Tests

## Phase 7 — F09 Notifications + F10 Settings + F11 Location

- [x] T7.1: `notification_service.dart` (FCM token, preferences)
- [x] T7.2: `notification_preference_section.dart`
- [x] T7.3: `settings_service.dart`
- [x] T7.4: `settings_screen.dart`
- [x] T7.5: `account_link_row.dart`, `report_dialog.dart`
- [x] T7.6: `location_service.dart`, `location_payload.dart`
- [x] T7.7: Tests

## Phase 8 — CI

- [x] T8.1: Cập nhật `.github/workflows/ci.yml` cho Flutter lint + test
