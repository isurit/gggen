plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "dev.dashboard.smartthings"
    compileSdk = 37
    defaultConfig {
        applicationId = "dev.dashboard.smartthings"
        minSdk = 26
        targetSdk = 36
        versionCode = 3
        versionName = "0.3"
        val apiUrl = providers.gradleProperty("pocApiUrl").orElse("https://localhost/api/a2ui/device-list").get()
        buildConfigField("String", "API_URL", "\"" + apiUrl + "\"")
        buildConfigField("String", "APP_KEY", "\"\"")
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies {
    implementation("androidx.activity:activity-compose:1.12.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.a2ui:a2ui-model:1.0.0-alpha02")
    implementation("androidx.a2ui:a2ui-engine:1.0.0-alpha02")
    implementation("androidx.a2ui.compose:compose-runtime:1.0.0-alpha02")
    implementation("androidx.a2ui.compose:compose-ui:1.0.0-alpha02")
    implementation("androidx.compose.material3:material3-a2ui:1.0.0-alpha02")
    implementation("androidx.compose.material3:material3:1.5.0-alpha06")
}
