plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.sih2026.nav"
    compileSdk = 34

    defaultConfig {
        // ".live" so this build installs next to the replay-only app already on the phone
        applicationId = "com.sih2026.nav.live"
        minSdk = 24
        targetSdk = 34
        versionCode = 2
        versionName = "2.0.0-live"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.11"
    }
    testOptions {
        unitTests.all {
            // reference runs from the Python engine (round2/phone/export_*.py) and the app's own assets
            it.systemProperty("fixtureDir", rootProject.file("../../data/osm/phone").absolutePath)
            it.systemProperty("assetDir", project.file("src/main/assets").absolutePath)
            it.systemProperty("drive", System.getProperty("drive") ?: "")      // DriveReplayTest: a recording or a folder
            for (key in listOf("readingRows", "maxTurnSpread", "heldSpeedSigma", "confirmSeconds", "verticalMinSpeed", "mountRecentS", "mountMinTurns")) it.systemProperty(key, System.getProperty(key) ?: "")   // tuning experiments
            it.maxHeapSize = "4g"
            it.testLogging { showStandardStreams = true; events("passed", "failed") }
        }
    }
    packaging {
        resources {
            excludes += "/META-INDEX/AL2.0"
            excludes += "/META-INDEX/LGPL2.1"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)

    // osmdroid for offline maps
    implementation(libs.osmdroid.android)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}
