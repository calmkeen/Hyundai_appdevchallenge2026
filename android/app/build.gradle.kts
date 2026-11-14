plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "com.carcue.app"
    compileSdk = 35
    defaultConfig {
        // A separate installed QA package proves first-install offline behavior without clearing user data.
        applicationId = providers.gradleProperty("carcueApplicationId").getOrElse("com.carcue.app").also {
            require(it in setOf("com.carcue.app", "com.carcue.app.offlineqa"))
        }
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "SERVER_URL", "\"${providers.gradleProperty("carcueServerUrl").getOrElse("http://10.0.2.2:8000")}\"")
        buildConfigField("long", "STATE_TTL_MS", "60000L")
    }
    flavorDimensions += "vehicle"
    productFlavors {
        create("demo") {
            dimension = "vehicle"
            applicationIdSuffix = ".demo"
            versionNameSuffix = "-mock"
            buildConfigField("boolean", "IS_MOCK", "true")
        }
        create("pleos") {
            dimension = "vehicle"
            buildConfigField("boolean", "IS_MOCK", "false")
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].assets.srcDir("../../content")
    useLibrary("android.car", false)
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}
dependencies {
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation(platform("androidx.compose:compose-bom:2024.04.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    add("pleosImplementation", "ai.pleos.playground:Vehicle:${providers.gradleProperty("pleosSdkVersion").getOrElse("2.3.2")}")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.04.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
