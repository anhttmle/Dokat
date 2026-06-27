# Flutter Migration — Design

## Tech Stack

| Concern            | Package                     | Thay thế RN                       |
|--------------------|-----------------------------|-----------------------------------|
| State management   | `flutter_riverpod ^2`       | Zustand stores                    |
| HTTP client        | `dio ^5`                    | fetch + service layer             |
| Firebase Auth      | `firebase_auth` (FlutterFire) | `@react-native-firebase/auth`   |
| Push notifications | `firebase_messaging`        | FCM RN                            |
| Navigation         | `go_router ^14`             | React Navigation 7                |
| Local storage      | `shared_preferences ^2`     | AsyncStorage                      |
| Camera             | `camera ^0.11`              | react-native-vision-camera        |
| Image picker       | `image_picker ^1`           | —                                 |
| QR generate        | `qr_flutter ^4`             | qrcode-svg                        |
| QR scan            | `mobile_scanner ^6`         | —                                 |
| AI on-device       | `tflite_flutter ^0.10`      | TFLite/CoreML RN bridge           |
| SVG                | `flutter_svg ^2`            | react-native-svg                  |
| Secure storage     | `flutter_secure_storage ^9` | —                                 |

## Cấu trúc thư mục `client/lib/`

```
client/lib/
├── main.dart                 # Entry: Firebase.initializeApp + runApp
├── app.dart                  # DokatApp widget (ProviderScope + router)
├── core/
│   ├── api_client.dart       # Dio singleton + Bearer token interceptor
│   ├── firebase_options.dart # FlutterFire CLI generated
│   └── constants.dart        # BASE_URL, hard limits
├── features/
│   ├── auth/                 # F01
│   │   ├── data/
│   │   │   └── auth_service.dart
│   │   ├── domain/
│   │   │   └── auth_state.dart
│   │   └── presentation/
│   │       ├── providers/
│   │       │   └── auth_notifier.dart
│   │       ├── screens/
│   │       │   └── force_link_screen.dart
│   │       └── widgets/
│   │           ├── auth_guard.dart
│   │           └── link_account_sheet.dart
│   ├── profile/              # F02
│   │   ├── data/
│   │   │   ├── profile_service.dart
│   │   │   └── pet_service.dart
│   │   ├── domain/
│   │   │   ├── owner_profile.dart
│   │   │   └── pet_profile.dart
│   │   └── presentation/
│   │       ├── providers/
│   │       │   ├── profile_notifier.dart
│   │       │   └── pet_notifier.dart
│   │       ├── screens/
│   │       │   ├── profile_screen.dart
│   │       │   └── pet_timeline_screen.dart
│   │       └── widgets/
│   │           ├── create_pet_sheet.dart
│   │           ├── edit_pet_sheet.dart
│   │           └── edit_owner_sheet.dart
│   ├── social/               # F03
│   │   ├── data/
│   │   │   └── social_service.dart
│   │   ├── domain/
│   │   │   └── friend.dart
│   │   └── presentation/
│   │       ├── providers/
│   │       │   └── friend_notifier.dart
│   │       ├── screens/
│   │       │   ├── friend_list_screen.dart
│   │       │   ├── add_friend_screen.dart
│   │       │   └── qr_scanner_screen.dart
│   │       └── widgets/
│   │           └── remove_friend_dialog.dart
│   ├── capture/              # F04
│   │   ├── data/
│   │   │   ├── capture_service.dart
│   │   │   ├── image_compressor.dart
│   │   │   └── pet_validation_service.dart
│   │   └── presentation/
│   │       ├── screens/
│   │       │   └── camera_screen.dart
│   │       └── widgets/
│   │           ├── pet_picker_overlay.dart
│   │           └── pet_selector_chip.dart
│   ├── send/                 # F05
│   │   ├── data/
│   │   │   └── send_service.dart
│   │   └── presentation/
│   │       └── screens/
│   │           └── recipient_selector_screen.dart
│   ├── feed/                 # F06
│   │   ├── data/
│   │   │   └── feed_service.dart
│   │   ├── domain/
│   │   │   └── post.dart
│   │   └── presentation/
│   │       ├── screens/
│   │       │   └── feed_screen.dart
│   │       └── widgets/
│   │           └── feed_item.dart
│   ├── seen/                 # F07
│   │   ├── data/
│   │   │   └── seen_service.dart
│   │   └── presentation/
│   │       └── widgets/
│   │           └── seen_by_list.dart
│   ├── history/              # F08
│   │   ├── data/
│   │   │   └── history_service.dart
│   │   └── presentation/
│   │       ├── screens/
│   │       │   └── history_screen.dart
│   │       └── widgets/
│   │           └── history_list.dart
│   ├── notifications/        # F09
│   │   ├── data/
│   │   │   └── notification_service.dart
│   │   └── presentation/
│   │       └── widgets/
│   │           └── notification_preference_section.dart
│   ├── settings/             # F10
│   │   ├── data/
│   │   │   └── settings_service.dart
│   │   └── presentation/
│   │       ├── screens/
│   │       │   └── settings_screen.dart
│   │       └── widgets/
│   │           ├── account_link_row.dart
│   │           └── report_dialog.dart
│   └── location/             # F11
│       ├── data/
│       │   └── location_service.dart
│       └── domain/
│           └── location_payload.dart
└── shared/
    ├── widgets/
    │   └── loading_overlay.dart
    └── utils/
        └── relative_time.dart
```

## Navigation (go_router)

```
GoRouter
├── /                     → redirect ke /feed (AuthGuard)
├── /force-link           → ForceLinkScreen (full-screen, no shell)
└── ShellRoute (BottomNavigationBar)
    ├── /feed             → FeedScreen
    ├── /friends          → FriendListScreen
    │   ├── /friends/add  → AddFriendScreen
    │   └── /friends/scan → QRScannerScreen
    ├── /history          → HistoryScreen
    └── /settings         → SettingsScreen
        ├── /profile      → ProfileScreen
        └── /profile/pet/:petId → PetTimelineScreen

/camera                   → CameraScreen (modal, outside shell)
/send/recipients          → RecipientSelectorScreen (modal, outside shell)
```

## State Management (Riverpod)

| RN Store           | Flutter Provider           | Type              |
|--------------------|----------------------------|-------------------|
| `useAuthStore`     | `authNotifierProvider`     | `AsyncNotifier`   |
| `useProfileStore`  | `profileNotifierProvider`  | `AsyncNotifier`   |
| `usePetStore`      | `petNotifierProvider`      | `AsyncNotifier`   |
| `useFriendStore`   | `friendNotifierProvider`   | `AsyncNotifier`   |
| —                  | `feedNotifierProvider`     | `AsyncNotifier`   |

## HTTP / API Client

`core/api_client.dart` tạo Dio instance với:
- `BaseOptions.baseUrl = Constants.BASE_URL`
- `InterceptorsWrapper.onRequest`: lấy `FirebaseAuth.instance.currentUser
  ?.getIdToken()` và set `Authorization: Bearer <token>`
- Tất cả service class nhận `Dio` qua constructor injection (dễ mock test).

## Testing

- Unit test: `flutter_test` + `mockito` cho services và providers.
- Widget test: `flutter_test` cho screens chính.
- Mocking: `mockito` generate mocks (`@GenerateMocks`).
- Test files mirror `lib/` trong `test/`.
