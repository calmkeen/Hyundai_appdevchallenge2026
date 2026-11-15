import java.net.URI
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Release credentials live outside source control. Missing credentials must never
// produce an unsigned release or fall back to the Android debug certificate.
val releasePropertiesPath = providers.environmentVariable("CARCUE_RELEASE_SIGNING_PROPERTIES")
    .orElse(providers.gradleProperty("carcueReleaseSigningProperties"))
val releaseProperties = Properties().apply {
    releasePropertiesPath.orNull?.let { path ->
        val source = rootProject.file(path)
        require(source.isFile) { "Release signing properties file is missing" }
        source.inputStream().use { load(it) }
    }
}
fun releaseSecret(environmentName: String, propertyName: String): String? =
    providers.environmentVariable(environmentName).orNull?.takeIf { it.isNotBlank() }
        ?: releaseProperties.getProperty(propertyName)?.takeIf { it.isNotBlank() }

val releaseStoreFile = releaseSecret("CARCUE_RELEASE_STORE_FILE", "storeFile")
val releaseStorePassword = releaseSecret("CARCUE_RELEASE_STORE_PASSWORD", "storePassword")
val releaseKeyAlias = releaseSecret("CARCUE_RELEASE_KEY_ALIAS", "keyAlias")
val releaseKeyPassword = releaseSecret("CARCUE_RELEASE_KEY_PASSWORD", "keyPassword")
val submissionAvd = providers.gradleProperty("carcueSubmissionAvd").map {
    require(it == "true" || it == "false") { "carcueSubmissionAvd must be true or false" }
    it == "true"
}.getOrElse(false)
val releaseServerUrl = providers.gradleProperty("carcueServerUrl").getOrElse(if (submissionAvd) "http://10.0.2.2:8001" else "")
val validateReleaseConfiguration = tasks.register("validateReleaseConfiguration") {
    doLast {
        require(listOf(releaseStoreFile, releaseStorePassword, releaseKeyAlias, releaseKeyPassword)
            .all { !it.isNullOrBlank() }) {
            "Release signing is required: set CARCUE_RELEASE_SIGNING_PROPERTIES or all CARCUE_RELEASE_* credentials"
        }
        require(rootProject.file(releaseStoreFile!!).isFile) { "Release keystore is missing" }
        val endpoint = URI(releaseServerUrl)
        require(endpoint.host != null && endpoint.rawUserInfo == null && endpoint.rawQuery == null && endpoint.rawFragment == null
            && (endpoint.scheme == "https" || (submissionAvd && endpoint.scheme == "http" && endpoint.host == "10.0.2.2"))) {
            "Release backend requires an explicit HTTPS URL; carcueSubmissionAvd=true permits only the 10.0.2.2 HTTP exception"
        }
    }
}
tasks.configureEach {
    if (name.matches(Regex("pre.*ReleaseBuild"))) dependsOn(validateReleaseConfiguration)
}
android {
    namespace = "com.carcue.app"
    compileSdk = 35
    defaultConfig {
        // A separate installed QA package proves first-install offline behavior without clearing user data.
        applicationId = providers.gradleProperty("carcueApplicationId").getOrElse("com.carcue.app").also {
            require(it in setOf("com.carcue.app", "com.carcue.app.offlineqa", "com.carcue.app.offlineqa2", "com.carcue.app.offlineqa3"))
        }
        minSdk = 28
        targetSdk = 35
        versionCode = 2
        versionName = "0.1.1-rc1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "SERVER_URL", "\"${providers.gradleProperty("carcueServerUrl").getOrElse("http://10.0.2.2:8000")}\"")
        buildConfigField("long", "STATE_TTL_MS", "60000L")
        buildConfigField("boolean", "ALLOW_STOCK_AVD_BROWSER", "false")
    }
    signingConfigs {
        create("release") {
            storeFile = releaseStoreFile?.let { rootProject.file(it) }
            storePassword = releaseStorePassword
            keyAlias = releaseKeyAlias
            keyPassword = releaseKeyPassword
        }
    }
    buildTypes {
        getByName("release") {
            isDebuggable = false
            signingConfig = signingConfigs.getByName("release")
            buildConfigField("boolean", "ALLOW_STOCK_AVD_BROWSER", submissionAvd.toString())
            buildConfigField("String", "SERVER_URL", "\"${releaseServerUrl.replace("\\", "\\\\").replace("\"", "\\\"")}\"")
            manifestPlaceholders["carcueNetworkSecurityConfig"] = if (submissionAvd)
                "@xml/submission_network_security_config" else "@xml/release_network_security_config"
        }
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
