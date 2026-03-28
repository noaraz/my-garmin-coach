# GarminCoach Mobile App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Android-first KMP + Compose Multiplatform mobile client for GarminCoach that shows today's workout, a weekly calendar, and a Garmin sync button — architected for easy iOS expansion.

**Architecture:** New `garmin-coach-mobile/` subdirectory in the existing repo. A `shared/` KMP module holds all business logic (API models, Ktor client, repositories, ViewModels, Koin modules) in `commonMain`. `androidApp/` holds the Compose UI and platform DI wiring. `expect/actual` interfaces isolate platform-specific code (TokenStorage, GoogleSignIn, BaseUrl) so iOS support is additive.

**Tech Stack:** Kotlin Multiplatform, Compose Multiplatform, Ktor 2.3, Koin 3.5, kotlinx.serialization 1.6, kotlinx.coroutines 1.8, Turbine 1.1, kotlin.test, play-services-auth 21, EncryptedSharedPreferences, GitHub Actions (mobile/v* release tags).

**Spec:** `docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md`

---

## Chunk 1: Foundation

### Phase 0: Documentation + Feature Directory Setup

**Files:**
- Create: `docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md`
- Create: `features/mobile-app/PLAN.md`
- Create: `features/mobile-app/CLAUDE.md`
- Modify: `STATUS.md`
- Modify: `PLAN.md` (root)
- Modify: `CLAUDE.md` (root)

- [ ] **Step 1: Create the feature directory**

```bash
mkdir -p features/mobile-app
```

- [ ] **Step 2: Write `features/mobile-app/PLAN.md`**

```markdown
# Mobile App Feature Plan

## Goal
Android-first KMP + Compose Multiplatform app. New client for existing FastAPI backend.
No App Store distribution — sideloaded APK. iOS expansion additive later.

## Status
- [ ] Phase 0: Docs setup
- [ ] Phase 1: Backend mobile auth endpoint
- [ ] Phase 2: KMP project scaffold
- [ ] Phase 3: API models
- [ ] Phase 4: Ktor client
- [ ] Phase 5: expect/actual auth primitives
- [ ] Phase 6: Data layer (TDD)
- [ ] Phase 7: ViewModels (TDD)
- [ ] Phase 8: DI wiring + Android screens
- [ ] Phase 9: Release CI

## Spec
See `docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md`

## Key Decisions
- Auth: auth code flow via new `POST /api/v1/auth/google/mobile` backend endpoint
- Sync: `POST /api/v1/sync/all?fetch_days=7` (NOT `start`/`end` params)
- Templates fetched once on launch, cached in memory for name lookups
- JWT refresh: access_token only; refresh_token never rotated
- Release tags: `mobile/v*` — separate from web app `v*` tags
```

- [ ] **Step 3: Write `features/mobile-app/CLAUDE.md`**

```markdown
# Mobile App Feature — CLAUDE.md

## Module Layout
- `garmin-coach-mobile/shared/` — KMP module, all business logic in commonMain
- `garmin-coach-mobile/androidApp/` — Compose UI + Android-specific DI
- `garmin-coach-mobile/gradle/libs.versions.toml` — all dependency versions

## Critical Gotchas

### Auth code flow vs ID token
Android Credential Manager returns an ID token. The backend expects an access token.
Use `requestServerAuthCode()` → send auth_code to `POST /api/v1/auth/google/mobile`.
Do NOT embed `GOOGLE_CLIENT_SECRET` in the app — backend exchanges the code server-side.

### Sync endpoint uses `fetch_days`, not `start`/`end`
`POST /api/v1/sync/all?fetch_days=7` — pass 7 days from mobile. Default is 30 days
(expensive on Neon free tier). Never omit `fetch_days`.

### Template names are NOT in the calendar response
`ScheduledWorkoutWithActivity` has `workout_template_id: Int?` but NOT the name.
`WorkoutRepositoryImpl` fetches the full template library once on app launch and caches
in memory. ViewModels look up names by ID from this cache.

### JWT refresh — no rotation
`POST /api/v1/auth/refresh` returns `{ access_token }` only. Keep original refresh_token.
`TokenStorage.updateAccessToken()` updates only the access_token.

### expect/actual for iOS readiness
`TokenStorage`, `GoogleSignIn`, `BaseUrl` are `expect class`/`expect object` in commonMain.
Android actuals live in `shared/androidMain/auth/`. iOS stubs in `shared/iosMain/auth/`.
Never add Android imports to `shared/commonMain/`.

### Koin module split
- `networkModule` (commonMain): HttpClient with bearer auth + refresh
- `appModule` (commonMain): repositories + viewModels
- `platformModule` (androidApp): Android actuals (TokenStorage, GoogleSignIn, BaseUrl)
All three loaded in `GarminCoachApplication.onCreate()`.

### iOS compile check
`./gradlew :shared:compileKotlinIosSimulatorArm64` — run to verify no Android
imports leaked into commonMain. This target does NOT require Xcode.

### Release tags
`mobile/v*` triggers `.github/workflows/mobile-release.yml`.
Web app releases use `v*` — the two tag namespaces are independent.

## Running Tests
```bash
cd garmin-coach-mobile
./gradlew :shared:jvmTest          # fast unit tests (commonTest on JVM)
./gradlew :shared:compileKotlinIosSimulatorArm64   # iOS compile check
./gradlew :androidApp:assembleDebug               # Android build
```

## File Patterns
- Repository: `data/<feature>/` — interface + impl + remote DS + local DS (NoOp)
- ViewModel: `viewmodel/<Name>ViewModel.kt` + state sealed class in same file
- Fakes: `commonTest/fakes/Fake<Name>.kt` — implement the interface, configurable output
- Koin modules: `di/AppModule.kt` + `di/NetworkModule.kt` (commonMain)
```

- [ ] **Step 4: Write the spec doc (copy from brainstorm output)**

Copy the full content of `/Users/noa.raz/.claude/plans/polished-painting-fox.md` to
`docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md`.
Remove the plan-file header lines (first 6 lines), keep everything from `# GarminCoach Mobile App — Design Spec` onward.

- [ ] **Step 5: Update `STATUS.md` — add mobile app entry**

Find the features table in `STATUS.md` and add:

```
| Mobile App | 🚧 In Progress | KMP + CMP Android app (iOS-ready), auth code flow, Koin DI, TDD |
```

- [ ] **Step 6: Update root `PLAN.md` — add mobile app row**

In the feature table, add:
```
| Mobile App | `features/mobile-app/` | KMP + Compose Multiplatform Android client |
```

- [ ] **Step 7: Update root `CLAUDE.md` — add mobile app section**

Add to the Features table in root `CLAUDE.md`:
```
| Mobile App | `features/mobile-app/` | KMP + Compose Multiplatform Android client; see features/mobile-app/CLAUDE.md |
```

Also add a brief note in the "Stack" section or under a new "Mobile" heading:
```
**Mobile:** garmin-coach-mobile/ — KMP + Compose Multiplatform (Android-first).
See features/mobile-app/CLAUDE.md for gotchas (auth code flow, sync params, interface-based DI).
Release tags: mobile/v* — separate from web app v* tags.
```

- [ ] **Step 8: Commit docs**

```bash
git add features/mobile-app/ docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md STATUS.md PLAN.md CLAUDE.md
git commit -m "docs: add mobile app feature directory, spec, and plan"
```

---

### Phase 1: Backend — Mobile Auth Endpoint

**Files:**
- Modify: `backend/src/core/config.py` — add `google_client_secret`
- Modify: `backend/src/auth/schemas.py` — add `MobileGoogleAuthRequest`
- Modify: `backend/src/auth/service.py` — add `mobile_google_auth()` function
- Modify: `backend/src/api/routers/auth.py` — add `POST /auth/google/mobile` route
- Modify: `.env.example` — add `GOOGLE_CLIENT_SECRET=`
- Modify: `docker-compose.yml` — add `GOOGLE_CLIENT_SECRET` env var
- Test: `backend/tests/integration/test_api_auth.py` — add mobile auth tests

**Context:** The existing `POST /api/v1/auth/google` endpoint expects a Google **access token** validated via the `tokeninfo` endpoint. The mobile app cannot embed `client_secret`, so Android uses `requestServerAuthCode()` to get a one-time auth code. The new endpoint exchanges this code server-side.

- [ ] **Step 1: Add `google_client_secret` to Settings**

In `backend/src/core/config.py`, add to the `Settings` class:
```python
google_client_secret: str = ""
```

- [ ] **Step 2: Add `MobileGoogleAuthRequest` schema**

In `backend/src/auth/schemas.py`, add:
```python
class MobileGoogleAuthRequest(BaseModel):
    auth_code: str
    invite_code: Optional[str] = None
```

- [ ] **Step 3: Write the failing test first**

In `backend/tests/integration/test_api_auth.py`, add:
```python
async def test_mobile_google_auth_exchanges_code_and_returns_tokens(
    self, client: AsyncClient, session: AsyncSession
) -> None:
    with (
        patch("src.auth.service.httpx.AsyncClient") as mock_http,
        patch("src.auth.service.google.oauth2.id_token.verify_oauth2_token") as mock_verify,
    ):
        # Mock Google token exchange
        mock_http.return_value.__aenter__.return_value.post.return_value.json.return_value = {
            "access_token": "goog_access",
            "id_token": "goog_id_token",
        }
        mock_verify.return_value = {
            "email": "mobile@example.com",
            "sub": "google_sub_mobile",
            "aud": "test-client-id",
        }
        resp = await client.post(
            "/api/v1/auth/google/mobile",
            json={"auth_code": "test_auth_code"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
```

- [ ] **Step 4: Run test to confirm RED**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_auth.py -k "test_mobile_google_auth" -v --no-cov
```
Expected: FAIL — `404 Not Found` (route doesn't exist yet)

- [ ] **Step 5: Implement `mobile_google_auth()` in service**

In `backend/src/auth/service.py`, add a new function (do NOT modify `_google_userinfo`):
```python
async def mobile_google_auth(
    auth_code: str,
    invite_code: Optional[str],
    session: AsyncSession,
    settings: Settings,
) -> TokenResponse:
    """Exchange Android auth code server-side and return JWT tokens."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": auth_code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

    id_token_str = token_data.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="no id_token in google response")

    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid google id token") from exc

    email: str = claims["email"]
    google_sub: str = claims["sub"]

    # Reuse existing user lookup / invite-code logic
    return await _find_or_create_user(
        email=email,
        google_sub=google_sub,
        invite_code=invite_code,
        session=session,
    )
```

Note: `_find_or_create_user` is the extracted shared logic. If the existing service has user lookup inline in `google_auth`, extract it into a private helper first.

- [ ] **Step 6: Add route in `auth.py`**

In `backend/src/api/routers/auth.py`:
```python
@router.post("/google/mobile", response_model=TokenResponse)
async def mobile_google_auth_route(
    request: MobileGoogleAuthRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    return await mobile_google_auth(
        auth_code=request.auth_code,
        invite_code=request.invite_code,
        session=session,
        settings=settings,
    )
```

- [ ] **Step 7: Run test to confirm GREEN**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_auth.py -k "test_mobile_google_auth" -v --no-cov
```
Expected: PASS

- [ ] **Step 8: Update env files**

`.env.example` — add:
```
GOOGLE_CLIENT_SECRET=
```

`docker-compose.yml` — add under backend environment:
```yaml
GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET:-}
```

- [ ] **Step 9: Run full auth test suite**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_auth.py -v --no-cov
```
Expected: all PASS

- [ ] **Step 10: Commit backend change**

```bash
git add backend/src/core/config.py backend/src/auth/schemas.py backend/src/auth/service.py backend/src/api/routers/auth.py .env.example docker-compose.yml backend/tests/integration/test_api_auth.py
git commit -m "feat: add POST /api/v1/auth/google/mobile endpoint for Android auth code flow"
```

---

## Chunk 2: KMP Project Scaffold

### Phase 2: KMP Project Setup

**Files (all new under `garmin-coach-mobile/`):**
- Create: `garmin-coach-mobile/settings.gradle.kts`
- Create: `garmin-coach-mobile/build.gradle.kts`
- Create: `garmin-coach-mobile/gradle/libs.versions.toml`
- Create: `garmin-coach-mobile/shared/build.gradle.kts`
- Create: `garmin-coach-mobile/androidApp/build.gradle.kts`
- Create: `garmin-coach-mobile/androidApp/src/main/AndroidManifest.xml`
- Create: `garmin-coach-mobile/.gitignore`

**Context:** This is a standard KMP + Android project. The `shared` module uses `kotlin("multiplatform")` + `id("com.android.library")`. The `androidApp` module uses `id("com.android.application")` + `id("org.jetbrains.compose")`. Use the Kotlin Gradle DSL throughout.

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p garmin-coach-mobile/shared/src/{commonMain,androidMain,iosMain,commonTest}/kotlin
mkdir -p garmin-coach-mobile/shared/src/commonMain/sqldelight/app
mkdir -p garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android
mkdir -p garmin-coach-mobile/gradle
```

- [ ] **Step 2: Write `garmin-coach-mobile/gradle/libs.versions.toml`**

```toml
[versions]
kotlin = "1.9.23"
agp = "8.3.1"
compose-multiplatform = "1.6.2"
ktor = "2.3.10"
koin = "3.5.3"
koin-compose = "3.5.3"
kotlinx-serialization = "1.6.3"
kotlinx-coroutines = "1.8.0"
turbine = "1.1.0"
security-crypto = "1.1.0-alpha06"
play-services-auth = "21.0.0"
sqldelight = "2.0.2"
navigation-compose = "2.7.7"

[libraries]
ktor-client-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }
ktor-client-okhttp = { module = "io.ktor:ktor-client-okhttp", version.ref = "ktor" }
ktor-client-cio = { module = "io.ktor:ktor-client-cio", version.ref = "ktor" }
ktor-client-content-negotiation = { module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }
ktor-serialization-kotlinx-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-client-auth = { module = "io.ktor:ktor-client-auth", version.ref = "ktor" }
koin-core = { module = "io.insert-koin:koin-core", version.ref = "koin" }
koin-android = { module = "io.insert-koin:koin-android", version.ref = "koin" }
koin-compose = { module = "io.insert-koin:koin-androidx-compose", version.ref = "koin-compose" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "kotlinx-serialization" }
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "kotlinx-coroutines" }
kotlinx-coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "kotlinx-coroutines" }
turbine = { module = "app.cash.turbine:turbine", version.ref = "turbine" }
security-crypto = { module = "androidx.security:security-crypto", version.ref = "security-crypto" }
play-services-auth = { module = "com.google.android.gms:play-services-auth", version.ref = "play-services-auth" }
navigation-compose = { module = "androidx.navigation:navigation-compose", version.ref = "navigation-compose" }

[plugins]
kotlin-multiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
android-application = { id = "com.android.application", version.ref = "agp" }
android-library = { id = "com.android.library", version.ref = "agp" }
compose-multiplatform = { id = "org.jetbrains.compose", version.ref = "compose-multiplatform" }
sqldelight = { id = "app.cash.sqldelight", version.ref = "sqldelight" }
```

- [ ] **Step 3: Write `garmin-coach-mobile/settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
    versionCatalogs {
        create("libs") {
            from(files("gradle/libs.versions.toml"))
        }
    }
}

rootProject.name = "GarminCoachMobile"
include(":shared")
include(":androidApp")
```

- [ ] **Step 4: Write `garmin-coach-mobile/build.gradle.kts` (root)**

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform) apply false
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.compose.multiplatform) apply false
}
```

- [ ] **Step 5: Write `garmin-coach-mobile/shared/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.android.library)
}

kotlin {
    androidTarget {
        compilations.all {
            kotlinOptions { jvmTarget = "17" }
        }
    }
    iosSimulatorArm64()  // compile-check — does NOT require Xcode

    sourceSets {
        commonMain.dependencies {
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.kotlinx.json)
            implementation(libs.ktor.client.auth)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.koin.core)
            implementation(libs.kotlinx.coroutines.core)
        }
        androidMain.dependencies {
            implementation(libs.ktor.client.okhttp)
            implementation(libs.koin.android)
            implementation(libs.security.crypto)
            implementation(libs.play.services.auth)
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.kotlinx.coroutines.test)
            implementation(libs.turbine)
        }
    }
}

android {
    namespace = "com.garmincoach.shared"
    compileSdk = 34
    defaultConfig { minSdk = 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
```

- [ ] **Step 6: Write `garmin-coach-mobile/androidApp/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.garmincoach.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.garmincoach.android"
        minSdk = 26
        targetSdk = 34
        // Read from Gradle property (-P flag) first, then env var, then default
        // CI passes -PMOBILE_VERSION_CODE=... which sets a Gradle property, not an env var
        versionCode = ((project.findProperty("MOBILE_VERSION_CODE") as String?)
            ?: System.getenv("MOBILE_VERSION_CODE") ?: "1").toInt()
        versionName = (project.findProperty("MOBILE_VERSION_NAME") as String?)
            ?: System.getenv("MOBILE_VERSION_NAME") ?: "1.0.0-dev"

        buildConfigField("String", "BASE_URL", "\"https://garmincoach.onrender.com\"")
    }

    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    androidTarget {
        compilations.all {
            kotlinOptions { jvmTarget = "17" }
        }
    }

    sourceSets {
        androidMain.dependencies {
            implementation(project(":shared"))
            implementation(libs.koin.android)
            implementation(libs.koin.compose)
            implementation(libs.navigation.compose)
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.ui)
        }
    }
}
```

- [ ] **Step 7: Write `garmin-coach-mobile/androidApp/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:name=".GarminCoachApplication"
        android:label="GarminCoach"
        android:theme="@style/Theme.AppCompat.DayNight.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- [ ] **Step 8: Write `garmin-coach-mobile/.gitignore`**

```
.gradle/
build/
*.keystore
local.properties
.idea/
*.iml
*.DS_Store
```

- [ ] **Step 9: Verify Gradle sync (smoke check)**

```bash
cd garmin-coach-mobile && ./gradlew :shared:compileKotlinAndroid --dry-run 2>&1 | tail -5
```
Expected: task graph printed, no configuration errors.

- [ ] **Step 10: Commit scaffold**

```bash
git add garmin-coach-mobile/
git commit -m "chore: scaffold KMP project (shared + androidApp, Gradle skeleton)"
```

---

## Chunk 3: API Models + Ktor Client

### Phase 3: API Models

**Files (all new under `garmin-coach-mobile/shared/src/commonMain/`):**
- Create: `api/models/GarminActivityRead.kt`
- Create: `api/models/ScheduledWorkoutWithActivity.kt`
- Create: `api/models/CalendarResponse.kt`
- Create: `api/models/WorkoutTemplate.kt`
- Create: `api/models/AuthModels.kt`
- Create: `api/models/SyncResult.kt`

**Context:** These are Kotlin data classes annotated with `@Serializable`. Field names match the FastAPI JSON responses exactly. Use `@SerialName` only where the field name differs from the backend.

- [ ] **Step 1: Write `GarminActivityRead.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GarminActivityRead(
    val id: Int,
    @SerialName("garmin_activity_id") val garminActivityId: Long,
    val name: String,
    @SerialName("sport_type") val sportType: String,
    @SerialName("start_time") val startTime: String,
    @SerialName("duration_sec") val durationSec: Int?,
    @SerialName("distance_m") val distanceM: Float?,
    @SerialName("avg_hr") val avgHr: Int?,
    @SerialName("compliance_status") val complianceStatus: String?,
)
```

- [ ] **Step 2: Write `ScheduledWorkoutWithActivity.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ScheduledWorkoutWithActivity(
    val id: Int,
    val date: String,                                  // YYYY-MM-DD
    @SerialName("workout_template_id") val workoutTemplateId: Int?,
    val notes: String?,
    val completed: Boolean,
    @SerialName("resolved_steps") val resolvedSteps: String?,
    @SerialName("garmin_workout_id") val garminWorkoutId: Long?,
    @SerialName("sync_status") val syncStatus: String?,
    @SerialName("matched_activity_id") val matchedActivityId: Int?,
    val activity: GarminActivityRead?,
)
```

- [ ] **Step 3: Write `CalendarResponse.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CalendarResponse(
    val workouts: List<ScheduledWorkoutWithActivity>,
    @SerialName("unplanned_activities") val unplannedActivities: List<GarminActivityRead>,
)
```

- [ ] **Step 4: Write `WorkoutTemplate.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class WorkoutTemplate(
    val id: Int,
    val name: String,
    val description: String?,
    @SerialName("sport_type") val sportType: String,
    @SerialName("estimated_duration_sec") val estimatedDurationSec: Int?,
    @SerialName("estimated_distance_m") val estimatedDistanceM: Float?,
    val tags: List<String> = emptyList(),
    val steps: String?,  // raw JSON, parsed only in detail view
)
```

- [ ] **Step 5: Write `AuthModels.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MobileAuthRequest(
    @SerialName("auth_code") val authCode: String,
    @SerialName("invite_code") val inviteCode: String? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class AuthResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("token_type") val tokenType: String,
)

@Serializable
data class RefreshResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String,
)
```

- [ ] **Step 6: Write `SyncResult.kt`**

```kotlin
package com.garmincoach.shared.api.models

import kotlinx.serialization.Serializable

@Serializable
data class SyncResult(
    val pushed: Int,
    val matched: Int,
    val errors: Int,
)
```

- [ ] **Step 7: Commit models**

```bash
git add garmin-coach-mobile/shared/src/commonMain/
git commit -m "feat: add API models (CalendarResponse, WorkoutTemplate, AuthModels, SyncResult)"
```

---

### Phase 4: Ktor Client + API Classes

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/api/ApiClient.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/api/AuthApi.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/api/CalendarApi.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/api/WorkoutApi.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/api/SyncApi.kt`

**Context:** `ApiClient.kt` configures a single `HttpClient` with `ContentNegotiation`, `Auth` bearer plugin (auto-refresh on 401), and a `defaultRequest` baseUrl. The Auth plugin's `refreshTokens` lambda calls `AuthApi.refresh()`. Each `*Api` class takes the `HttpClient` as a constructor parameter.

- [ ] **Step 1: Write `ApiClient.kt`**

```kotlin
package com.garmincoach.shared.api

import com.garmincoach.shared.api.models.RefreshRequest
import com.garmincoach.shared.auth.TokenStorage
import io.ktor.client.*
import io.ktor.client.plugins.auth.*
import io.ktor.client.plugins.auth.providers.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.request.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json

fun createHttpClient(
    tokenStorage: TokenStorage,
    baseUrl: String,
    engine: io.ktor.client.engine.HttpClientEngine,
): HttpClient = HttpClient(engine) {
    install(ContentNegotiation) {
        json(Json {
            ignoreUnknownKeys = true
            isLenient = true
        })
    }
    install(Auth) {
        bearer {
            loadTokens {
                val access = tokenStorage.getAccessToken() ?: return@loadTokens null
                BearerTokens(access, tokenStorage.getRefreshToken() ?: "")
            }
            refreshTokens {
                val refreshToken = tokenStorage.getRefreshToken() ?: return@refreshTokens null
                val response = client.post("${baseUrl}api/v1/auth/refresh") {
                    contentType(io.ktor.http.ContentType.Application.Json)
                    setBody(RefreshRequest(refreshToken))
                    markAsRefreshTokenRequest()
                }
                val refreshed = response.body<com.garmincoach.shared.api.models.RefreshResponse>()
                tokenStorage.updateAccessToken(refreshed.accessToken)
                BearerTokens(refreshed.accessToken, refreshToken)
            }
        }
    }
    defaultRequest { url(baseUrl) }
}
```

- [ ] **Step 2: Write `AuthApi.kt`**

```kotlin
package com.garmincoach.shared.api

import com.garmincoach.shared.api.models.AuthResponse
import com.garmincoach.shared.api.models.MobileAuthRequest
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*
import io.ktor.http.*

class AuthApi(private val client: HttpClient) {
    suspend fun mobileAuth(authCode: String, inviteCode: String?): AuthResponse =
        client.post("api/v1/auth/google/mobile") {
            contentType(ContentType.Application.Json)
            setBody(MobileAuthRequest(authCode = authCode, inviteCode = inviteCode))
        }.body()
}
```

- [ ] **Step 3: Write `CalendarApi.kt`**

```kotlin
package com.garmincoach.shared.api

import com.garmincoach.shared.api.models.CalendarResponse
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*

class CalendarApi(private val client: HttpClient) {
    suspend fun getCalendar(start: String, end: String): CalendarResponse =
        client.get("api/v1/calendar/") {
            parameter("start", start)
            parameter("end", end)
        }.body()
}
```

- [ ] **Step 4: Write `WorkoutApi.kt`**

The backend route is `GET /api/v1/workouts/` (the router prefix is `/api/v1/workouts`, and the list endpoint is at `/`). Confirmed in `backend/src/api/routers/workouts.py` — `@router.get("/", response_model=List[WorkoutTemplateRead])`.

```kotlin
package com.garmincoach.shared.api

import com.garmincoach.shared.api.models.WorkoutTemplate
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*

class WorkoutApi(private val client: HttpClient) {
    // GET /api/v1/workouts/ — returns full template list (name, description, sport_type, etc.)
    suspend fun getTemplates(): List<WorkoutTemplate> =
        client.get("api/v1/workouts/").body()
}
```

- [ ] **Step 5: Write `SyncApi.kt`**

```kotlin
package com.garmincoach.shared.api

import com.garmincoach.shared.api.models.SyncResult
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*

class SyncApi(private val client: HttpClient) {
    /** Always pass fetchDays explicitly — default is 30 which is too expensive. Use 7. */
    suspend fun syncAll(fetchDays: Int = 7): SyncResult =
        client.post("api/v1/sync/all") {
            parameter("fetch_days", fetchDays)
        }.body()
}
```

- [ ] **Step 6: Commit API layer**

```bash
git add garmin-coach-mobile/shared/src/commonMain/api/
git commit -m "feat: add Ktor API client and API classes (Auth, Calendar, Workout, Sync)"
```

---

## Chunk 4: expect/actual + Auth Primitives

### Phase 5: expect/actual Auth Primitives

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/auth/TokenStorage.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/auth/GoogleSignIn.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/auth/BaseUrl.kt`
- Create: `garmin-coach-mobile/shared/src/androidMain/auth/TokenStorage.kt`
- Create: `garmin-coach-mobile/shared/src/androidMain/auth/GoogleSignIn.kt`
- Create: `garmin-coach-mobile/shared/src/androidMain/auth/BaseUrl.kt`
- Create: `garmin-coach-mobile/shared/src/iosMain/auth/TokenStorage.kt`
- Create: `garmin-coach-mobile/shared/src/iosMain/auth/GoogleSignIn.kt`
- Create: `garmin-coach-mobile/shared/src/iosMain/auth/BaseUrl.kt`

**Context:** `expect` declarations live in `commonMain`. Android `actual` implementations use `EncryptedSharedPreferences` (TokenStorage), `GoogleSignInClient.requestServerAuthCode()` (GoogleSignIn), and `BuildConfig.BASE_URL` (BaseUrl). iOS actuals are stubs with `TODO()`.

- [ ] **Step 1: Write `commonMain/auth/TokenStorage.kt`**

Use an **interface** (not `expect class`) so it can be implemented in `commonTest` fakes without platform complications:

```kotlin
package com.garmincoach.shared.auth

// Interface — implemented by platform actuals and by test fakes
interface TokenStorage {
    suspend fun saveTokens(accessToken: String, refreshToken: String)
    suspend fun updateAccessToken(accessToken: String)
    suspend fun getAccessToken(): String?
    suspend fun getRefreshToken(): String?
    suspend fun clear()
}
```

- [ ] **Step 2: Write `commonMain/auth/GoogleSignIn.kt`**

```kotlin
package com.garmincoach.shared.auth

data class GoogleAuthResult(val authCode: String, val email: String)

expect class GoogleSignIn {
    suspend fun signIn(): GoogleAuthResult
    suspend fun signOut()
}
```

- [ ] **Step 3: Write `commonMain/auth/BaseUrl.kt`**

```kotlin
package com.garmincoach.shared.auth

expect object BaseUrl {
    val value: String
}
```

- [ ] **Step 4: Write `androidMain/auth/TokenStorage.kt`**

```kotlin
package com.garmincoach.shared.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys

class TokenStorageAndroid(private val context: Context) : TokenStorage {
    private val prefs by lazy {
        EncryptedSharedPreferences.create(
            "garmincoach_tokens",
            MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
            context,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    override suspend fun saveTokens(accessToken: String, refreshToken: String) {
        prefs.edit()
            .putString("access_token", accessToken)
            .putString("refresh_token", refreshToken)
            .apply()
    }

    override suspend fun updateAccessToken(accessToken: String) {
        prefs.edit().putString("access_token", accessToken).apply()
    }

    override suspend fun getAccessToken(): String? = prefs.getString("access_token", null)
    override suspend fun getRefreshToken(): String? = prefs.getString("refresh_token", null)

    override suspend fun clear() {
        prefs.edit().clear().apply()
    }
}
```

- [ ] **Step 5: Write `androidMain/auth/GoogleSignIn.kt`**

```kotlin
package com.garmincoach.shared.auth

import android.content.Context
import android.content.Intent
import com.google.android.gms.auth.api.signin.GoogleSignIn as GmsGoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * serverClientId: the Web OAuth 2.0 client ID from Google Cloud Console.
 * Passed from PlatformModule (read from android resources) — NOT hardcoded here.
 * This is NOT the Android client ID; it must match the redirect_uri "postmessage" registration.
 */
class GoogleSignInAndroid(
    private val context: Context,
    private val serverClientId: String,
) : GoogleSignIn {

    private fun buildClient() = GmsGoogleSignIn.getClient(
        context,
        GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestServerAuthCode(serverClientId, true)
            .requestEmail()
            .build()
    )

    /**
     * Shows the Google account picker. Use this for both first-time and repeat sign-in.
     * Do NOT use silentSignIn() as it fails for new users.
     *
     * Caller (Activity/Fragment) must call startActivityForResult with the Intent
     * returned by client.signInIntent, then pass the result back via handleSignInResult().
     * For Compose, use ActivityResultContracts.StartActivityForResult launcher.
     *
     * This suspend function uses a callback bridge — wire the launcher before calling signIn().
     */
    override suspend fun signIn(): GoogleAuthResult = suspendCancellableCoroutine { cont ->
        buildClient().signOut().addOnCompleteListener {
            // signOut first ensures a fresh account picker (not cached silent sign-in)
            // The actual sign-in Intent must be launched from an Activity:
            // val intent = buildClient().signInIntent
            // launcher.launch(intent) → in onActivityResult parse via:
            // GmsGoogleSignIn.getSignedInAccountFromIntent(data).result.serverAuthCode
            //
            // For a simple implementation, trigger from the LoginScreen using rememberLauncherForActivityResult:
            // val launcher = rememberLauncherForActivityResult(StartActivityForResult()) { result ->
            //     val account = GmsGoogleSignIn.getSignedInAccountFromIntent(result.data).result
            //     viewModel.onGoogleSignInResult(account.serverAuthCode!!, account.email!!)
            // }
            cont.resumeWithException(
                UnsupportedOperationException(
                    "GoogleSignIn.signIn() must be triggered from the Compose launcher. " +
                    "See LoginScreen implementation notes."
                )
            )
        }
    }

    override suspend fun signOut() = suspendCancellableCoroutine<Unit> { cont ->
        buildClient().signOut().addOnCompleteListener { cont.resume(Unit) }
    }

    /** Call this from the Activity result handler with the Intent from startActivityForResult. */
    fun handleSignInResult(data: Intent?): GoogleAuthResult {
        val account = GmsGoogleSignIn.getSignedInAccountFromIntent(data).getResult(Exception::class.java)
        val authCode = account.serverAuthCode
            ?: throw IllegalStateException("No auth code in Google Sign-In result")
        return GoogleAuthResult(authCode = authCode, email = account.email ?: "")
    }
}
```

**Implementation note for `LoginScreen.kt`:** Replace the `vm.signIn()` call with an Activity Result launcher:
```kotlin
val googleSignIn = koinInject<GoogleSignIn>() as GoogleSignInAndroid
val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
    val authResult = googleSignIn.handleSignInResult(result.data)
    vm.onSignInResult(authResult.authCode, authResult.email)
}
Button(onClick = { launcher.launch(googleSignIn.buildClient().signInIntent) }) {
    Text("Sign in with Google")
}
```

Add `fun buildClient()` as `internal fun` (remove `private`) so `LoginScreen` can access it.

- [ ] **Step 6: Write `androidMain/auth/BaseUrl.kt`**

```kotlin
package com.garmincoach.shared.auth

// Hardcoded here — overridden at build time via BuildConfig in androidApp.
// This avoids importing androidApp's BuildConfig from the shared module.
class BaseUrlAndroid(val value: String = "https://garmincoach.onrender.com/") : BaseUrl
```

Also update `commonMain/auth/BaseUrl.kt` to be an **interface** (not `expect object`):
```kotlin
// commonMain/auth/BaseUrl.kt
interface BaseUrl {
    val value: String
}
```

Update `PlatformModule.kt` (Phase 8) to bind:
```kotlin
single<BaseUrl> { BaseUrlAndroid(value = context.getString(R.string.base_url)) }
```
Add `res/values/config.xml` to `androidApp/src/main/res/values/`:
```xml
<resources>
    <string name="base_url">https://garmincoach.onrender.com/</string>
    <string name="google_server_client_id">YOUR_WEB_CLIENT_ID_HERE</string>
</resources>
```
`GoogleSignInAndroid` reads `context.getString(R.string.google_server_client_id)` — no `BuildConfig` import needed from shared.

- [ ] **Step 7: Write iOS stubs**

Since `TokenStorage`, `GoogleSignIn`, and `BaseUrl` are now **interfaces** (not `expect`), iOS does NOT need stubs in `iosMain`. The iOS target will compile fine because there are no `actual` declarations required.

Create iOS-specific implementations when adding iOS support later:
- `TokenStorageIos.kt` → implements `TokenStorage` using Keychain
- `GoogleSignInIos.kt` → implements `GoogleSignIn` using GoogleSignIn iOS SDK
- `BaseUrlIos.kt` → implements `BaseUrl` returning the prod URL

For now, confirm `iosMain/` source set exists but is empty (compilation target only):
```bash
mkdir -p garmin-coach-mobile/shared/src/iosMain/kotlin
touch garmin-coach-mobile/shared/src/iosMain/kotlin/.gitkeep
```

- [ ] **Step 8: Verify iOS compile check passes**

```bash
cd garmin-coach-mobile && ./gradlew :shared:compileKotlinIosSimulatorArm64
```
Expected: BUILD SUCCESSFUL (all expect/actual classes present)

- [ ] **Step 9: Add `GOOGLE_SERVER_CLIENT_ID` build config to `androidApp/build.gradle.kts`**

Inside `defaultConfig { }`:
```kotlin
buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", "\"YOUR_WEB_CLIENT_ID_HERE\"")
```
Replace `YOUR_WEB_CLIENT_ID_HERE` with the actual Web OAuth client ID. This is intentionally hardcoded for the dev build — not a secret (client IDs are public).

- [ ] **Step 10: Commit**

```bash
git add garmin-coach-mobile/shared/src/
git commit -m "feat: add expect/actual TokenStorage, GoogleSignIn, BaseUrl (Android + iOS stubs)"
```

---

## Chunk 5: Data Layer (TDD)

### Phase 6: Repository + Data Sources

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/data/calendar/CalendarRepository.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/calendar/CalendarRepositoryImpl.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/calendar/CalendarRemoteDataSource.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/calendar/CalendarLocalDataSource.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/workout/WorkoutRepository.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/workout/WorkoutRepositoryImpl.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/workout/WorkoutRemoteDataSource.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/auth/AuthRepository.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/data/auth/AuthRepositoryImpl.kt`
- Create: `garmin-coach-mobile/shared/src/commonTest/fakes/FakeCalendarRepository.kt`
- Create: `garmin-coach-mobile/shared/src/commonTest/fakes/FakeCalendarLocalDataSource.kt`
- Create: `garmin-coach-mobile/shared/src/commonTest/fakes/FakeCalendarRemoteDataSource.kt`
- Create: `garmin-coach-mobile/shared/src/commonTest/fakes/FakeWorkoutRepository.kt`
- Create: `garmin-coach-mobile/shared/src/commonTest/fakes/FakeTokenStorage.kt`
- Test: `garmin-coach-mobile/shared/src/commonTest/data/CalendarRepositoryTest.kt`

- [ ] **Step 1: Write interfaces first**

`CalendarRepository.kt`:
```kotlin
package com.garmincoach.shared.data.calendar

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity

interface CalendarRepository {
    suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity>
}
```

`CalendarRemoteDataSource.kt`:
```kotlin
package com.garmincoach.shared.data.calendar

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity

interface CalendarRemoteDataSource {
    suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity>
}
```

`CalendarLocalDataSource.kt`:
```kotlin
package com.garmincoach.shared.data.calendar

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity

interface CalendarLocalDataSource {
    suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity>
    suspend fun save(workouts: List<ScheduledWorkoutWithActivity>)
}
```

- [ ] **Step 2: Write fakes**

`FakeCalendarRemoteDataSource.kt`:
```kotlin
package com.garmincoach.shared.fakes

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity
import com.garmincoach.shared.data.calendar.CalendarRemoteDataSource

class FakeCalendarRemoteDataSource(
    private val workouts: List<ScheduledWorkoutWithActivity> = emptyList(),
    private val shouldFail: Boolean = false,
) : CalendarRemoteDataSource {
    override suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity> {
        if (shouldFail) throw Exception("network error")
        return workouts
    }
}
```

`FakeCalendarLocalDataSource.kt`:
```kotlin
package com.garmincoach.shared.fakes

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity
import com.garmincoach.shared.data.calendar.CalendarLocalDataSource

class FakeCalendarLocalDataSource(
    private val cached: List<ScheduledWorkoutWithActivity> = emptyList(),
) : CalendarLocalDataSource {
    val saved = mutableListOf<ScheduledWorkoutWithActivity>()
    override suspend fun getWorkouts(start: String, end: String) = cached
    override suspend fun save(workouts: List<ScheduledWorkoutWithActivity>) { saved.addAll(workouts) }
}
```

`FakeCalendarRepository.kt`:
```kotlin
package com.garmincoach.shared.fakes

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity
import com.garmincoach.shared.data.calendar.CalendarRepository

class FakeCalendarRepository(
    private val workouts: List<ScheduledWorkoutWithActivity> = emptyList(),
    private val shouldFail: Boolean = false,
) : CalendarRepository {
    override suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity> {
        if (shouldFail) throw Exception("network error")
        return workouts
    }
}
```

`FakeTokenStorage.kt`:
```kotlin
package com.garmincoach.shared.fakes

import com.garmincoach.shared.auth.TokenStorage

// Implements the TokenStorage interface — no platform concerns
class FakeTokenStorage(
    private var accessToken: String? = null,
    private var refreshToken: String? = null,
) : TokenStorage {
    override suspend fun saveTokens(accessToken: String, refreshToken: String) {
        this.accessToken = accessToken; this.refreshToken = refreshToken
    }
    override suspend fun updateAccessToken(accessToken: String) { this.accessToken = accessToken }
    override suspend fun getAccessToken() = accessToken
    override suspend fun getRefreshToken() = refreshToken
    override suspend fun clear() { accessToken = null; refreshToken = null }
}
```

- [ ] **Step 3: Write `CalendarRepositoryTest.kt` (TDD — test first)**

```kotlin
package com.garmincoach.shared.data

import com.garmincoach.shared.fakes.FakeCalendarLocalDataSource
import com.garmincoach.shared.fakes.FakeCalendarRemoteDataSource
import com.garmincoach.shared.data.calendar.CalendarRepositoryImpl
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.test.runTest

class CalendarRepositoryTest {

    @Test fun `returns remote data and caches locally`() = runTest {
        val remote = FakeCalendarRemoteDataSource(workouts = listOf(fakeWorkout("2026-03-27")))
        val local = FakeCalendarLocalDataSource()
        val repo = CalendarRepositoryImpl(remote, local)

        val result = repo.getWorkouts("2026-03-27", "2026-03-27")

        assertEquals(1, result.size)
        assertEquals(1, local.saved.size)  // cached
    }

    @Test fun `falls back to local cache when remote fails`() = runTest {
        val remote = FakeCalendarRemoteDataSource(shouldFail = true)
        val local = FakeCalendarLocalDataSource(cached = listOf(fakeWorkout("2026-03-27")))
        val repo = CalendarRepositoryImpl(remote, local)

        val result = repo.getWorkouts("2026-03-27", "2026-03-27")

        assertEquals(1, result.size)
    }

    @Test fun `returns empty list when remote fails and cache is empty`() = runTest {
        val repo = CalendarRepositoryImpl(
            FakeCalendarRemoteDataSource(shouldFail = true),
            FakeCalendarLocalDataSource(),
        )
        assertEquals(emptyList(), repo.getWorkouts("2026-03-27", "2026-03-27"))
    }
}

private fun fakeWorkout(date: String) = com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity(
    id = 1, date = date, workoutTemplateId = null, notes = null,
    completed = false, resolvedSteps = null, garminWorkoutId = null,
    syncStatus = null, matchedActivityId = null, activity = null,
)
```

- [ ] **Step 4: Run tests — confirm RED**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest --tests "*.CalendarRepositoryTest" 2>&1 | tail -10
```
Expected: FAIL — `CalendarRepositoryImpl` not found

- [ ] **Step 5: Implement `CalendarRepositoryImpl.kt`**

```kotlin
package com.garmincoach.shared.data.calendar

import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity

class CalendarRepositoryImpl(
    private val remote: CalendarRemoteDataSource,
    private val local: CalendarLocalDataSource,
) : CalendarRepository {
    override suspend fun getWorkouts(start: String, end: String): List<ScheduledWorkoutWithActivity> =
        try {
            remote.getWorkouts(start, end).also { local.save(it) }
        } catch (e: Exception) {
            local.getWorkouts(start, end)
        }
}
```

Also add `NoOpCalendarLocalDataSource`:
```kotlin
class NoOpCalendarLocalDataSource : CalendarLocalDataSource {
    override suspend fun getWorkouts(start: String, end: String) = emptyList<ScheduledWorkoutWithActivity>()
    override suspend fun save(workouts: List<ScheduledWorkoutWithActivity>) = Unit
}
```

- [ ] **Step 6: Run tests — confirm GREEN**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest --tests "*.CalendarRepositoryTest"
```
Expected: 3/3 PASS

- [ ] **Step 7: Add WorkoutRepository (same pattern)**

`WorkoutRepository.kt`:
```kotlin
interface WorkoutRepository {
    suspend fun getTemplates(): List<com.garmincoach.shared.api.models.WorkoutTemplate>
    fun findById(id: Int): com.garmincoach.shared.api.models.WorkoutTemplate?
}
```

`WorkoutRemoteDataSource.kt`:
```kotlin
interface WorkoutRemoteDataSource {
    suspend fun getTemplates(): List<com.garmincoach.shared.api.models.WorkoutTemplate>
}
```

`WorkoutRepositoryImpl.kt` — fetches on first call, caches in memory:
```kotlin
class WorkoutRepositoryImpl(
    private val remote: WorkoutRemoteDataSource,
) : WorkoutRepository {
    private val cache = mutableListOf<com.garmincoach.shared.api.models.WorkoutTemplate>()

    override suspend fun getTemplates(): List<com.garmincoach.shared.api.models.WorkoutTemplate> {
        if (cache.isEmpty()) cache.addAll(remote.getTemplates())
        return cache.toList()
    }

    override fun findById(id: Int) = cache.find { it.id == id }
}
```

`FakeWorkoutRepository.kt`:
```kotlin
class FakeWorkoutRepository(
    private val templates: List<com.garmincoach.shared.api.models.WorkoutTemplate> = emptyList(),
) : WorkoutRepository {
    override suspend fun getTemplates() = templates
    override fun findById(id: Int) = templates.find { it.id == id }
}
```

- [ ] **Step 8: Add AuthRepository**

`AuthRepository.kt`:
```kotlin
interface AuthRepository {
    suspend fun loginWithAuthCode(authCode: String, inviteCode: String?): Unit
    suspend fun refreshToken(): String  // returns new access token
    suspend fun logout()
    suspend fun isLoggedIn(): Boolean
}
```

`AuthRepositoryImpl.kt`:
```kotlin
class AuthRepositoryImpl(
    private val authApi: com.garmincoach.shared.api.AuthApi,
    private val tokenStorage: com.garmincoach.shared.auth.TokenStorage,
) : AuthRepository {
    override suspend fun loginWithAuthCode(authCode: String, inviteCode: String?) {
        val response = authApi.mobileAuth(authCode, inviteCode)
        tokenStorage.saveTokens(response.accessToken, response.refreshToken)
    }

    override suspend fun refreshToken(): String {
        // Ktor Auth plugin calls this via HttpClient — we just need to signal the new token
        return tokenStorage.getAccessToken() ?: throw IllegalStateException("No access token")
    }

    override suspend fun logout() = tokenStorage.clear()

    override suspend fun isLoggedIn() = tokenStorage.getAccessToken() != null
}
```

- [ ] **Step 9: Commit data layer**

```bash
git add garmin-coach-mobile/shared/src/
git commit -m "feat: add repository + data source layer with TDD (Calendar, Workout, Auth)"
```

---

## Chunk 6: ViewModels (TDD)

### Phase 7: ViewModels

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/viewmodel/TodayViewModel.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/viewmodel/CalendarViewModel.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/viewmodel/AuthViewModel.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/viewmodel/SyncViewModel.kt`
- Test: `garmin-coach-mobile/shared/src/commonTest/viewmodel/TodayViewModelTest.kt`
- Test: `garmin-coach-mobile/shared/src/commonTest/viewmodel/CalendarViewModelTest.kt`
- Test: `garmin-coach-mobile/shared/src/commonTest/viewmodel/AuthViewModelTest.kt`

**Context:** ViewModels use `kotlinx.coroutines` `StateFlow` for UI state. They are NOT Android `ViewModel` — they are plain Kotlin classes in `commonMain`. Koin's `viewModel { }` block wraps them. Tests use `runTest` + Turbine's `.test { }` extension.

- [ ] **Step 1: Write `TodayViewModelTest.kt` (RED first)**

```kotlin
package com.garmincoach.shared.viewmodel

import app.cash.turbine.test
import com.garmincoach.shared.fakes.FakeCalendarRepository
import com.garmincoach.shared.fakes.FakeWorkoutRepository
import com.garmincoach.shared.api.models.ScheduledWorkoutWithActivity
import com.garmincoach.shared.api.models.WorkoutTemplate
import kotlin.test.Test
import kotlin.test.assertIs
import kotlin.test.assertEquals
import kotlinx.coroutines.test.runTest

class TodayViewModelTest {

    private fun fakeWorkout(templateId: Int?) = ScheduledWorkoutWithActivity(
        id = 1, date = "2026-03-27", workoutTemplateId = templateId, notes = null,
        completed = false, resolvedSteps = null, garminWorkoutId = null,
        syncStatus = null, matchedActivityId = null, activity = null,
    )
    private fun fakeTemplate(id: Int, name: String) = WorkoutTemplate(
        id = id, name = name, description = null, sportType = "running",
        estimatedDurationSec = 3600, estimatedDistanceM = null, steps = null,
    )

    @Test fun `emits Loading then Success with workout name`() = runTest {
        val template = fakeTemplate(42, "Easy 60min")
        val vm = TodayViewModel(
            calendarRepo = FakeCalendarRepository(workouts = listOf(fakeWorkout(templateId = 42))),
            workoutRepo = FakeWorkoutRepository(templates = listOf(template)),
        )
        vm.uiState.test {
            assertIs<TodayUiState.Loading>(awaitItem())
            val success = awaitItem() as TodayUiState.Success
            assertEquals("Easy 60min", success.workoutName)
        }
    }

    @Test fun `emits Empty when no workout today`() = runTest {
        val vm = TodayViewModel(
            calendarRepo = FakeCalendarRepository(workouts = emptyList()),
            workoutRepo = FakeWorkoutRepository(),
        )
        vm.uiState.test {
            assertIs<TodayUiState.Loading>(awaitItem())
            assertIs<TodayUiState.Empty>(awaitItem())
        }
    }

    @Test fun `emits Error when repo fails`() = runTest {
        val vm = TodayViewModel(
            calendarRepo = FakeCalendarRepository(shouldFail = true),
            workoutRepo = FakeWorkoutRepository(),
        )
        vm.uiState.test {
            assertIs<TodayUiState.Loading>(awaitItem())
            assertIs<TodayUiState.Error>(awaitItem())
        }
    }
}
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest --tests "*.TodayViewModelTest" 2>&1 | tail -5
```
Expected: FAIL — `TodayViewModel` not found

- [ ] **Step 3: Implement `TodayViewModel.kt`**

```kotlin
package com.garmincoach.shared.viewmodel

import com.garmincoach.shared.data.calendar.CalendarRepository
import com.garmincoach.shared.data.workout.WorkoutRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.datetime.Clock
import kotlinx.datetime.TimeZone
import kotlinx.datetime.todayIn

sealed class TodayUiState {
    object Loading : TodayUiState()
    object Empty : TodayUiState()
    data class Error(val message: String) : TodayUiState()
    data class Success(
        val workoutName: String,
        val syncStatus: String?,
        val isCompleted: Boolean,
    ) : TodayUiState()
}

class TodayViewModel(
    private val calendarRepo: CalendarRepository,
    private val workoutRepo: WorkoutRepository,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Default),
) {
    private val _uiState = MutableStateFlow<TodayUiState>(TodayUiState.Loading)
    val uiState: StateFlow<TodayUiState> = _uiState

    init { load() }

    fun load() {
        scope.launch {
            _uiState.value = TodayUiState.Loading
            try {
                val today = Clock.System.todayIn(TimeZone.currentSystemDefault()).toString()
                workoutRepo.getTemplates()  // warm cache
                val workouts = calendarRepo.getWorkouts(today, today)
                val todayWorkout = workouts.firstOrNull()
                if (todayWorkout == null) {
                    _uiState.value = TodayUiState.Empty
                    return@launch
                }
                val name = todayWorkout.workoutTemplateId
                    ?.let { workoutRepo.findById(it)?.name }
                    ?: "Workout"
                _uiState.value = TodayUiState.Success(
                    workoutName = name,
                    syncStatus = todayWorkout.syncStatus,
                    isCompleted = todayWorkout.completed,
                )
            } catch (e: Exception) {
                _uiState.value = TodayUiState.Error(e.message ?: "Unknown error")
            }
        }
    }
}
```

Note: Add `org.jetbrains.kotlinx:kotlinx-datetime` to `commonMain.dependencies` in `shared/build.gradle.kts` (add `kotlinx-datetime = "0.5.0"` to versions toml).

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest --tests "*.TodayViewModelTest"
```
Expected: 3/3 PASS

- [ ] **Step 5: Implement `CalendarViewModel.kt` with tests**

`CalendarViewModelTest.kt`:
```kotlin
@Test fun `emits week of workouts`() = runTest {
    val workouts = (0..6).map { fakeWorkout("2026-03-2${it}", templateId = 1) }
    val vm = CalendarViewModel(
        calendarRepo = FakeCalendarRepository(workouts = workouts),
        workoutRepo = FakeWorkoutRepository(templates = listOf(fakeTemplate(1, "Easy Run"))),
    )
    vm.uiState.test {
        assertIs<CalendarUiState.Loading>(awaitItem())
        val success = awaitItem() as CalendarUiState.Success
        assertEquals(7, success.workouts.size)
    }
}
```

`CalendarViewModel.kt`:
```kotlin
sealed class CalendarUiState {
    object Loading : CalendarUiState()
    data class Error(val message: String) : CalendarUiState()
    data class Success(val workouts: List<WorkoutDay>) : CalendarUiState()
}

data class WorkoutDay(
    val date: String,
    val workoutName: String?,
    val isCompleted: Boolean,
    val syncStatus: String?,
)

class CalendarViewModel(
    private val calendarRepo: CalendarRepository,
    private val workoutRepo: WorkoutRepository,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Default),
) {
    private val _uiState = MutableStateFlow<CalendarUiState>(CalendarUiState.Loading)
    val uiState: StateFlow<CalendarUiState> = _uiState

    fun loadWeek(start: String, end: String) {
        scope.launch {
            _uiState.value = CalendarUiState.Loading
            try {
                workoutRepo.getTemplates()
                val workouts = calendarRepo.getWorkouts(start, end)
                _uiState.value = CalendarUiState.Success(
                    workouts.map { sw ->
                        WorkoutDay(
                            date = sw.date,
                            workoutName = sw.workoutTemplateId?.let { workoutRepo.findById(it)?.name },
                            isCompleted = sw.completed,
                            syncStatus = sw.syncStatus,
                        )
                    }
                )
            } catch (e: Exception) {
                _uiState.value = CalendarUiState.Error(e.message ?: "Unknown error")
            }
        }
    }
}
```

- [ ] **Step 6: Implement `AuthViewModel.kt`**

**Key pattern:** Cache the Google `authCode` from the launcher result so it can be reused on invite-code retry without re-triggering Google Sign-In. The 403 body detail is parsed from Ktor's `ClientRequestException`.

```kotlin
sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    object Success : AuthUiState()
    /** 403 — invite code required. authCode cached for retry. */
    object NeedsInviteCode : AuthUiState()
    data class Error(val message: String) : AuthUiState()
}

class AuthViewModel(
    private val authRepo: AuthRepository,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Default),
) {
    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    /** Cached from the Google Sign-In launcher result. Reused on invite-code retry. */
    private var pendingAuthCode: String? = null

    /** Called by LoginScreen's ActivityResult launcher once Google returns an auth code. */
    fun onSignInResult(authCode: String, email: String, inviteCode: String? = null) {
        pendingAuthCode = authCode
        attemptLogin(authCode, inviteCode)
    }

    /** Called when user submits invite code after NeedsInviteCode state. */
    fun retryWithInviteCode(inviteCode: String) {
        val code = pendingAuthCode ?: run {
            _uiState.value = AuthUiState.Error("Session expired — please sign in again")
            return
        }
        attemptLogin(code, inviteCode)
    }

    private fun attemptLogin(authCode: String, inviteCode: String?) {
        scope.launch {
            _uiState.value = AuthUiState.Loading
            try {
                authRepo.loginWithAuthCode(authCode, inviteCode)
                _uiState.value = AuthUiState.Success
            } catch (e: io.ktor.client.plugins.ClientRequestException) {
                if (e.response.status.value == 403) {
                    _uiState.value = AuthUiState.NeedsInviteCode
                } else {
                    _uiState.value = AuthUiState.Error(e.message ?: "Auth failed")
                }
            } catch (e: Exception) {
                _uiState.value = AuthUiState.Error(e.message ?: "Auth failed")
            }
        }
    }

    fun logout() { scope.launch { authRepo.logout(); _uiState.value = AuthUiState.Idle } }
}
```

**`LoginScreen.kt` update:** Replace `vm.signIn()` button call with:
```kotlin
val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
    val googleSignInAndroid = koinInject<GoogleSignIn>() as GoogleSignInAndroid
    val authResult = googleSignInAndroid.handleSignInResult(result.data)
    vm.onSignInResult(authResult.authCode, authResult.email)
}

// Show invite field when NeedsInviteCode
if (state is AuthUiState.NeedsInviteCode) {
    OutlinedTextField(value = inviteCode, onValueChange = { inviteCode = it }, label = { Text("Invite Code") })
    Button(onClick = { vm.retryWithInviteCode(inviteCode) }) { Text("Continue") }
} else {
    Button(onClick = { launcher.launch(googleSignInAndroid.buildClient().signInIntent) }) {
        Text("Sign in with Google")
    }
}
```

- [ ] **Step 6b: Write `AuthViewModelTest.kt` (TDD — RED first)**

```kotlin
package com.garmincoach.shared.viewmodel

import app.cash.turbine.test
import com.garmincoach.shared.fakes.FakeAuthRepository
import kotlin.test.Test
import kotlin.test.assertIs
import kotlinx.coroutines.test.runTest

class AuthViewModelTest {

    @Test fun `emits Loading then Success on valid auth code`() = runTest {
        val repo = FakeAuthRepository(shouldSucceed = true)
        val vm = AuthViewModel(authRepo = repo)
        vm.uiState.test {
            assertIs<AuthUiState.Idle>(awaitItem())
            vm.onSignInResult("valid_code", "user@test.com")
            assertIs<AuthUiState.Loading>(awaitItem())
            assertIs<AuthUiState.Success>(awaitItem())
        }
    }

    @Test fun `emits NeedsInviteCode on 403 response`() = runTest {
        val repo = FakeAuthRepository(throwHttpCode = 403)
        val vm = AuthViewModel(authRepo = repo)
        vm.uiState.test {
            assertIs<AuthUiState.Idle>(awaitItem())
            vm.onSignInResult("code", "user@test.com")
            assertIs<AuthUiState.Loading>(awaitItem())
            assertIs<AuthUiState.NeedsInviteCode>(awaitItem())
        }
    }

    @Test fun `retryWithInviteCode reuses cached auth code`() = runTest {
        val repo = FakeAuthRepository(throwHttpCode = 403, succeedOnRetry = true)
        val vm = AuthViewModel(authRepo = repo)
        vm.uiState.test {
            assertIs<AuthUiState.Idle>(awaitItem())
            vm.onSignInResult("code", "user@test.com")
            assertIs<AuthUiState.Loading>(awaitItem())
            assertIs<AuthUiState.NeedsInviteCode>(awaitItem())
            vm.retryWithInviteCode("INVITE123")
            assertIs<AuthUiState.Loading>(awaitItem())
            assertIs<AuthUiState.Success>(awaitItem())
        }
    }
}
```

`FakeAuthRepository.kt`:
```kotlin
class FakeAuthRepository(
    private val shouldSucceed: Boolean = true,
    private val throwHttpCode: Int? = null,
    private val succeedOnRetry: Boolean = false,
) : AuthRepository {
    private var callCount = 0
    override suspend fun loginWithAuthCode(authCode: String, inviteCode: String?) {
        callCount++
        when {
            throwHttpCode == 403 && !succeedOnRetry -> throw FakeHttpException(403)
            throwHttpCode == 403 && callCount == 1 -> throw FakeHttpException(403)
            !shouldSucceed -> throw Exception("auth failed")
        }
    }
    override suspend fun refreshToken() = "new_access_token"
    override suspend fun logout() = Unit
    override suspend fun isLoggedIn() = false
}

class FakeHttpException(val code: Int) : Exception("HTTP $code")
```

Note: `FakeHttpException` is test-only. In `AuthViewModel` (production code in `commonMain`), only catch `ClientRequestException`:
```kotlin
} catch (e: io.ktor.client.plugins.ClientRequestException) {
    if (e.response.status.value == 403) _uiState.value = AuthUiState.NeedsInviteCode
    else _uiState.value = AuthUiState.Error(e.message ?: "Auth failed")
} catch (e: Exception) {
    _uiState.value = AuthUiState.Error(e.message ?: "Auth failed")
}
```
`FakeAuthRepository` should throw a real `ClientRequestException` in tests, or the test can verify the `NeedsInviteCode` state is reachable by making `FakeAuthRepository` throw a thin subclass. Simplest: have `FakeAuthRepository.throwHttpCode = 403` set `_uiState.value = AuthUiState.NeedsInviteCode` directly by subclassing a `TestClientRequestException` that sets `statusCode = 403`.

- [ ] **Step 7: Implement `SyncViewModel.kt`**

```kotlin
sealed class SyncUiState {
    object Idle : SyncUiState()
    object Syncing : SyncUiState()
    data class Done(val pushed: Int, val matched: Int) : SyncUiState()
    data class Error(val message: String) : SyncUiState()
}

class SyncViewModel(
    private val syncApi: SyncApi,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Default),
) {
    private val _uiState = MutableStateFlow<SyncUiState>(SyncUiState.Idle)
    val uiState: StateFlow<SyncUiState> = _uiState

    fun sync(fetchDays: Int = 7) {
        scope.launch {
            _uiState.value = SyncUiState.Syncing
            try {
                val result = syncApi.syncAll(fetchDays)
                _uiState.value = SyncUiState.Done(result.pushed, result.matched)
            } catch (e: Exception) {
                _uiState.value = SyncUiState.Error(e.message ?: "Sync failed")
            }
        }
    }
}
```

- [ ] **Step 8: Run all shared tests**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest
```
Expected: all PASS

- [ ] **Step 9: Commit ViewModels**

```bash
git add garmin-coach-mobile/shared/src/
git commit -m "feat: add ViewModels with TDD (Today, Calendar, Auth, Sync)"
```

---

## Chunk 7: DI + Android Screens

### Phase 8: Koin DI Wiring + Android Screens

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/di/NetworkModule.kt`
- Create: `garmin-coach-mobile/shared/src/commonMain/di/AppModule.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/di/PlatformModule.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/GarminCoachApplication.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/MainActivity.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/navigation/NavHost.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/screens/LoginScreen.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/screens/TodayScreen.kt`
- Create: `garmin-coach-mobile/androidApp/src/main/kotlin/com/garmincoach/android/screens/CalendarScreen.kt`

- [ ] **Step 1: Write `NetworkModule.kt`**

**IMPORTANT:** Place in `androidApp/src/main/kotlin/com/garmincoach/android/di/NetworkModule.kt`, NOT in `shared/commonMain/`. The OkHttp engine import (`io.ktor.client.engine.okhttp.OkHttp`) is Android-only and will break the iOS compile check if placed in `commonMain`. When iOS is added, create a parallel `iosMain` version using `CIO`.

```kotlin
package com.garmincoach.android.di

import com.garmincoach.shared.api.*
import com.garmincoach.shared.auth.BaseUrl
import com.garmincoach.shared.auth.TokenStorage
import io.ktor.client.engine.okhttp.OkHttp
import org.koin.dsl.module

val networkModule = module {
    single {
        createHttpClient(
            tokenStorage = get<TokenStorage>(),
            baseUrl = get<BaseUrl>().value,
            engine = OkHttp.create(),
        )
    }
    single { AuthApi(get()) }
    single { CalendarApi(get()) }
    single { WorkoutApi(get()) }
    single { SyncApi(get()) }
}
```

Update `GarminCoachApplication.kt` import: `import com.garmincoach.android.di.networkModule`.

- [ ] **Step 2: Write `AppModule.kt`**

```kotlin
package com.garmincoach.shared.di

import com.garmincoach.shared.data.auth.*
import com.garmincoach.shared.data.calendar.*
import com.garmincoach.shared.data.workout.*
import com.garmincoach.shared.viewmodel.*
import org.koin.dsl.module

val appModule = module {
    single<CalendarRemoteDataSource> { CalendarRemoteDataSourceImpl(get()) }
    single<CalendarLocalDataSource> { NoOpCalendarLocalDataSource() }
    single<CalendarRepository> { CalendarRepositoryImpl(get(), get()) }

    single<WorkoutRemoteDataSource> { WorkoutRemoteDataSourceImpl(get()) }
    single<WorkoutRepository> { WorkoutRepositoryImpl(get()) }

    single<AuthRepository> { AuthRepositoryImpl(get(), get()) }

    factory { TodayViewModel(get(), get()) }
    factory { CalendarViewModel(get(), get()) }
    factory { AuthViewModel(get()) }   // AuthViewModel(authRepo: AuthRepository) — CoroutineScope uses default
    factory { SyncViewModel(get()) }
}
```

Note: Add `CalendarRemoteDataSourceImpl` and `WorkoutRemoteDataSourceImpl` — thin wrappers around the respective API classes:
```kotlin
class CalendarRemoteDataSourceImpl(private val api: CalendarApi) : CalendarRemoteDataSource {
    override suspend fun getWorkouts(start: String, end: String) =
        api.getCalendar(start, end).workouts
}
class WorkoutRemoteDataSourceImpl(private val api: WorkoutApi) : WorkoutRemoteDataSource {
    override suspend fun getTemplates() = api.getTemplates()
}
```

- [ ] **Step 3: Write `PlatformModule.kt` (Android)**

```kotlin
package com.garmincoach.android.di

import com.garmincoach.shared.auth.BaseUrl
import com.garmincoach.shared.auth.BaseUrlAndroid
import com.garmincoach.shared.auth.GoogleSignIn
import com.garmincoach.shared.auth.GoogleSignInAndroid
import com.garmincoach.shared.auth.TokenStorage
import com.garmincoach.shared.auth.TokenStorageAndroid
import org.koin.android.ext.koin.androidContext
import org.koin.dsl.module
import com.garmincoach.android.R

val platformModule = module {
    single<TokenStorage> { TokenStorageAndroid(androidContext()) }
    single<GoogleSignIn> {
        GoogleSignInAndroid(
            context = androidContext(),
            serverClientId = androidContext().getString(R.string.google_server_client_id),
        )
    }
    single<BaseUrl> { BaseUrlAndroid(value = androidContext().getString(R.string.base_url)) }
}
```

- [ ] **Step 4: Write `GarminCoachApplication.kt`**

```kotlin
package com.garmincoach.android

import android.app.Application
import com.garmincoach.android.di.networkModule   // ← androidApp/di/, NOT shared/di/
import com.garmincoach.android.di.platformModule
import com.garmincoach.shared.di.appModule
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin

class GarminCoachApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@GarminCoachApplication)
            modules(networkModule, appModule, platformModule)
        }
    }
}
```

- [ ] **Step 5: Write `NavHost.kt`**

```kotlin
package com.garmincoach.android.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.garmincoach.android.screens.CalendarScreen
import com.garmincoach.android.screens.LoginScreen
import com.garmincoach.android.screens.TodayScreen

@Composable
fun GarminCoachNavHost(isLoggedIn: Boolean) {
    val navController = rememberNavController()
    val startDest = if (isLoggedIn) "today" else "login"

    NavHost(navController, startDestination = startDest) {
        composable("login") {
            LoginScreen(onLoginSuccess = { navController.navigate("today") { popUpTo("login") { inclusive = true } } })
        }
        composable("today") {
            TodayScreen(onNavigateCalendar = { navController.navigate("calendar") })
        }
        composable("calendar") {
            CalendarScreen()
        }
    }
}
```

- [ ] **Step 6: Write `LoginScreen.kt`**

```kotlin
package com.garmincoach.android.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.garmincoach.shared.auth.GoogleSignIn
import com.garmincoach.shared.auth.GoogleSignInAndroid
import com.garmincoach.shared.viewmodel.AuthUiState
import com.garmincoach.shared.viewmodel.AuthViewModel
import org.koin.androidx.compose.koinInject
import org.koin.androidx.compose.koinViewModel

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    val vm: AuthViewModel = koinViewModel()
    val googleSignIn = koinInject<GoogleSignIn>() as GoogleSignInAndroid
    val state by vm.uiState.collectAsState()

    var inviteCode by remember { mutableStateOf("") }

    // ActivityResult launcher for Google Sign-In — must be called before any conditional returns
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val authResult = googleSignIn.handleSignInResult(result.data)
        vm.onSignInResult(authResult.authCode, authResult.email)
    }

    LaunchedEffect(state) {
        if (state is AuthUiState.Success) onLoginSuccess()
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("GarminCoach", style = MaterialTheme.typography.headlineLarge)
        Spacer(Modifier.height(32.dp))

        if (state is AuthUiState.NeedsInviteCode) {
            OutlinedTextField(
                value = inviteCode,
                onValueChange = { inviteCode = it },
                label = { Text("Invite Code") },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = { vm.retryWithInviteCode(inviteCode) },
                enabled = inviteCode.isNotBlank() && state !is AuthUiState.Loading,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Continue") }
        } else {
            Button(
                onClick = { launcher.launch(googleSignIn.buildClient().signInIntent) },
                enabled = state !is AuthUiState.Loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state is AuthUiState.Loading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp))
                } else {
                    Text("Sign in with Google")
                }
            }
        }

        if (state is AuthUiState.Error) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = (state as AuthUiState.Error).message,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}
```

Note: `buildClient()` must be `internal fun` in `GoogleSignInAndroid` (not `private`) so this screen can call it.

- [ ] **Step 7: Write `TodayScreen.kt`**

```kotlin
package com.garmincoach.android.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.garmincoach.shared.viewmodel.*
import org.koin.androidx.compose.koinViewModel

@Composable
fun TodayScreen(onNavigateCalendar: () -> Unit) {
    val todayVm: TodayViewModel = koinViewModel()
    val syncVm: SyncViewModel = koinViewModel()
    val todayState by todayVm.uiState.collectAsState()
    val syncState by syncVm.uiState.collectAsState()

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { syncVm.sync(fetchDays = 7) }) {
                if (syncState is SyncUiState.Syncing) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Icon(Icons.Default.Sync, contentDescription = "Sync")
                }
            }
        },
        topBar = {
            TopAppBar(
                title = { Text("Today") },
                actions = {
                    TextButton(onClick = onNavigateCalendar) { Text("Calendar") }
                }
            )
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (val s = todayState) {
                is TodayUiState.Loading -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                is TodayUiState.Empty -> Text("Rest day!", Modifier.align(Alignment.Center))
                is TodayUiState.Error -> Text("Error: ${s.message}", Modifier.align(Alignment.Center))
                is TodayUiState.Success -> Column(Modifier.padding(16.dp)) {
                    Text(s.workoutName, style = MaterialTheme.typography.headlineMedium)
                    Spacer(Modifier.height(8.dp))
                    s.syncStatus?.let { Text("Sync: $it", style = MaterialTheme.typography.bodySmall) }
                    if (s.isCompleted) Text("✓ Completed", color = MaterialTheme.colorScheme.primary)
                }
            }
        }
        if (syncState is SyncUiState.Done) {
            val done = syncState as SyncUiState.Done
            // Show a snackbar or toast — simple Text for now
        }
    }
}
```

- [ ] **Step 8: Write `CalendarScreen.kt`**

```kotlin
package com.garmincoach.android.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.garmincoach.shared.viewmodel.*
import kotlinx.datetime.*
import org.koin.androidx.compose.koinViewModel

@Composable
fun CalendarScreen() {
    val vm: CalendarViewModel = koinViewModel()
    val state by vm.uiState.collectAsState()

    val today = Clock.System.todayIn(TimeZone.currentSystemDefault())
    val weekStart = today.minus(today.dayOfWeek.ordinal, DateTimeUnit.DAY).toString()
    val weekEnd = today.plus(6 - today.dayOfWeek.ordinal, DateTimeUnit.DAY).toString()

    LaunchedEffect(Unit) { vm.loadWeek(weekStart, weekEnd) }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text("This Week") })
        when (val s = state) {
            is CalendarUiState.Loading -> LinearProgressIndicator(Modifier.fillMaxWidth())
            is CalendarUiState.Error -> Text("Error: ${s.message}", Modifier.padding(16.dp))
            is CalendarUiState.Success -> LazyColumn {
                items(s.workouts) { day ->
                    ListItem(
                        headlineContent = { Text(day.workoutName ?: "Rest") },
                        supportingContent = { Text(day.date) },
                        trailingContent = {
                            if (day.isCompleted) Text("✓")
                        },
                        modifier = Modifier.padding(horizontal = 8.dp),
                    )
                    HorizontalDivider()
                }
            }
        }
    }
}
```

- [ ] **Step 9: Write `MainActivity.kt`**

```kotlin
package com.garmincoach.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import com.garmincoach.android.navigation.GarminCoachNavHost
import com.garmincoach.shared.auth.TokenStorage
import kotlinx.coroutines.runBlocking
import org.koin.android.ext.android.inject

class MainActivity : ComponentActivity() {
    private val tokenStorage: TokenStorage by inject()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val isLoggedIn = runBlocking { tokenStorage.getAccessToken() != null }
        setContent {
            MaterialTheme {
                GarminCoachNavHost(isLoggedIn = isLoggedIn)
            }
        }
    }
}
```

- [ ] **Step 10: Build Android APK**

```bash
cd garmin-coach-mobile && ./gradlew :androidApp:assembleDebug
```
Expected: BUILD SUCCESSFUL, APK at `androidApp/build/outputs/apk/debug/androidApp-debug.apk`

- [ ] **Step 11: Commit DI + screens**

```bash
git add garmin-coach-mobile/
git commit -m "feat: wire Koin DI and implement Login, Today, Calendar screens"
```

---

## Chunk 8: Release CI

### Phase 9: GitHub Actions Release Workflow

**Files:**
- Create: `.github/workflows/mobile-release.yml`
- Create: `garmin-coach-mobile/androidApp/release-signing.gradle.kts` (signing config)

**Context:** Tags prefixed `mobile/v*` trigger the release build. APK is signed with a keystore stored as base64 in GitHub Secrets, then attached to a GitHub Release. Debug builds do not require signing and can be done locally with `adb install`.

- [ ] **Step 1: Write `.github/workflows/mobile-release.yml`**

```yaml
name: Mobile Release

on:
  push:
    tags:
      - 'mobile/v*'

jobs:
  build-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - name: Set up Gradle cache
        uses: gradle/actions/setup-gradle@v3

      - name: Extract version from tag
        id: version
        run: |
          TAG="${GITHUB_REF#refs/tags/mobile/v}"
          echo "version_name=$TAG" >> $GITHUB_OUTPUT
          # versionCode = YYMMDDhhmm (numeric, monotonically increasing)
          echo "version_code=$(date +%y%m%d%H%M)" >> $GITHUB_OUTPUT

      - name: Decode keystore
        run: |
          echo "${{ secrets.MOBILE_KEYSTORE_BASE64 }}" | base64 --decode > garmin-coach-mobile/keystore.jks

      - name: Build signed release APK
        working-directory: garmin-coach-mobile
        run: |
          ./gradlew :androidApp:assembleRelease \
            -PMOBILE_VERSION_CODE=${{ steps.version.outputs.version_code }} \
            -PMOBILE_VERSION_NAME=${{ steps.version.outputs.version_name }} \
            -PKEYSTORE_PATH=${{ github.workspace }}/garmin-coach-mobile/keystore.jks \
            -PKEYSTORE_PASSWORD=${{ secrets.MOBILE_KEYSTORE_PASSWORD }} \
            -PKEY_ALIAS=${{ secrets.MOBILE_KEY_ALIAS }} \
            -PKEY_PASSWORD=${{ secrets.MOBILE_KEY_PASSWORD }}

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: garmin-coach-mobile/androidApp/build/outputs/apk/release/androidApp-release.apk
          name: "Mobile ${{ steps.version.outputs.version_name }}"
          body: "Android APK — sideload with `adb install`"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Add signing config to `androidApp/build.gradle.kts`**

Inside the `android { }` block, add:
```kotlin
signingConfigs {
    create("release") {
        storeFile = file(project.findProperty("KEYSTORE_PATH") as String? ?: "keystore.jks")
        storePassword = project.findProperty("KEYSTORE_PASSWORD") as String? ?: ""
        keyAlias = project.findProperty("KEY_ALIAS") as String? ?: ""
        keyPassword = project.findProperty("KEY_PASSWORD") as String? ?: ""
    }
}
buildTypes {
    release {
        signingConfig = signingConfigs.getByName("release")
        isMinifyEnabled = true
        proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
    }
}
```

- [ ] **Step 3: Generate a debug keystore for local testing**

```bash
keytool -genkey -v \
  -keystore garmin-coach-mobile/debug-keystore.jks \
  -alias garmincoach \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass debugpass -keypass debugpass \
  -dname "CN=GarminCoach, O=Dev, C=IL"
```

Add `debug-keystore.jks` to `garmin-coach-mobile/.gitignore` (the one created in Phase 2, Step 8).

- [ ] **Step 4: Add GitHub Secrets (manual step)**

In the GitHub repo settings → Secrets and variables → Actions, add:
- `MOBILE_KEYSTORE_BASE64` — `base64 -i path/to/release.keystore`
- `MOBILE_KEYSTORE_PASSWORD` — keystore password
- `MOBILE_KEY_ALIAS` — key alias
- `MOBILE_KEY_PASSWORD` — key password

Document this in `features/mobile-app/PLAN.md` under a "Setup" section.

- [ ] **Step 5: Test the workflow with a dry-run tag**

```bash
git tag mobile/v0.1.0-test
git push origin mobile/v0.1.0-test
```
Watch GitHub Actions. Expected: release build succeeds, APK attached to a `mobile/v0.1.0-test` release.

- [ ] **Step 6: Commit CI workflow**

```bash
git add .github/workflows/mobile-release.yml garmin-coach-mobile/androidApp/build.gradle.kts
git commit -m "chore: add mobile release CI (mobile/v* tags → signed APK → GitHub Release)"
```

---

## Chunk 9: iOS Readiness Verification

### Phase 10: iOS Compile Check + SQLDelight Prep

**Files:**
- Create: `garmin-coach-mobile/shared/src/commonMain/sqldelight/app/.gitkeep`
- Modify: `garmin-coach-mobile/shared/build.gradle.kts` — add `iosSimulatorArm64` target (already there from Phase 2, verify)

- [ ] **Step 1: Verify iOS compile check**

```bash
cd garmin-coach-mobile && ./gradlew :shared:compileKotlinIosSimulatorArm64 2>&1 | tail -10
```
Expected: BUILD SUCCESSFUL — this confirms no Android imports leaked into `commonMain`.

If it fails: search for `import android.` in `shared/src/commonMain/` and move those files to `androidMain`:
```bash
grep -r "import android\." garmin-coach-mobile/shared/src/commonMain/
```

- [ ] **Step 2: Verify zero Android imports in shared commonMain**

```bash
grep -r "import android\." garmin-coach-mobile/shared/src/commonMain/ && echo "FOUND ANDROID IMPORTS — fix before proceeding" || echo "OK: no Android imports in commonMain"
```
Expected: `OK: no Android imports in commonMain`

- [ ] **Step 3: Pre-create SQLDelight schema directory**

```bash
mkdir -p garmin-coach-mobile/shared/src/commonMain/sqldelight/app
touch garmin-coach-mobile/shared/src/commonMain/sqldelight/app/.gitkeep
```

- [ ] **Step 4: Update `features/mobile-app/PLAN.md` — mark phases complete**

Update the phase checklist to reflect completed phases.

- [ ] **Step 5: Run full test suite one final time**

```bash
cd garmin-coach-mobile && ./gradlew :shared:jvmTest :androidApp:assembleDebug :shared:compileKotlinIosSimulatorArm64
```
Expected: all three tasks succeed.

- [ ] **Step 6: Final commit**

```bash
git add garmin-coach-mobile/shared/src/commonMain/sqldelight/ features/mobile-app/PLAN.md
git commit -m "chore: verify iOS compile check, pre-create SQLDelight schema dir"
```

---

## Summary: File Map

| Path | Purpose |
|------|---------|
| `features/mobile-app/PLAN.md` | Feature-level plan tracking |
| `features/mobile-app/CLAUDE.md` | Mobile gotchas, patterns, commands |
| `docs/superpowers/specs/2026-03-27-garmin-coach-mobile-design.md` | Full design spec |
| `garmin-coach-mobile/shared/src/commonMain/api/` | Ktor HttpClient + API classes |
| `garmin-coach-mobile/shared/src/commonMain/api/models/` | Serializable data classes |
| `garmin-coach-mobile/shared/src/commonMain/auth/` | expect/actual declarations |
| `garmin-coach-mobile/shared/src/androidMain/auth/` | Android actuals |
| `garmin-coach-mobile/shared/src/iosMain/auth/` | iOS stubs |
| `garmin-coach-mobile/shared/src/commonMain/data/` | Repository + data source interfaces |
| `garmin-coach-mobile/shared/src/commonMain/viewmodel/` | ViewModels + sealed UI state |
| `garmin-coach-mobile/shared/src/commonMain/di/` | Koin modules (shared) |
| `garmin-coach-mobile/androidApp/src/main/kotlin/.../di/` | Platform Koin module |
| `garmin-coach-mobile/androidApp/src/main/kotlin/.../screens/` | Compose UI screens |
| `.github/workflows/mobile-release.yml` | `mobile/v*` → signed APK release |
| `backend/src/api/routers/auth.py` | New `/auth/google/mobile` endpoint |
| `backend/src/auth/service.py` | `mobile_google_auth()` function |
