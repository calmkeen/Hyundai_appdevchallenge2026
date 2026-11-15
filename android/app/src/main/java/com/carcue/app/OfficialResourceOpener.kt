package com.carcue.app

import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.Uri

/** Delivery to an Android handler is not proof that a remote page loaded. No app/session data is added. */
internal class OfficialResourceOpener(private val context: Context) {
    var lastRoute = ExternalOpenRoute.STANDARD
        private set

    fun open(resource: ExternalResource): ExternalOpenResult {
        lastRoute = ExternalOpenRoute.STANDARD
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(resource.url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try {
            context.startActivity(intent)
            ExternalOpenResult.INTENT_DISPATCHED
        } catch (_: ActivityNotFoundException) {
            openStockAvdBrowser(intent)
        } catch (_: SecurityException) {
            ExternalOpenResult.REJECTED
        }
    }

    private fun openStockAvdBrowser(intent: Intent): ExternalOpenResult {
        // The official API34 image's Browser2 is exported but its VIEW filter lacks DEFAULT.
        // SDK debug or the explicitly selected submission AVD profile only; never download a browser.
        if (!stockAvdBrowserAllowed(BuildConfig.DEBUG, BuildConfig.ALLOW_STOCK_AVD_BROWSER,
                BuildConfig.IS_MOCK, android.os.Build.VERSION.SDK_INT, android.os.Build.HARDWARE))
            return ExternalOpenResult.NO_HANDLER
        val component = ComponentName("org.chromium.webview_shell", "org.chromium.webview_shell.WebViewBrowserActivity")
        val info = try {
            @Suppress("DEPRECATION")
            context.packageManager.getActivityInfo(component, 0)
        } catch (_: android.content.pm.PackageManager.NameNotFoundException) {
            return ExternalOpenResult.NO_HANDLER
        } catch (_: SecurityException) {
            return ExternalOpenResult.REJECTED
        }
        if (!info.exported || !info.enabled || !info.applicationInfo.enabled || !info.permission.isNullOrBlank() ||
            (info.applicationInfo.flags and ApplicationInfo.FLAG_SYSTEM) == 0 ||
            !info.applicationInfo.sourceDir.startsWith("/product/app/Browser2/")) return ExternalOpenResult.NO_HANDLER
        lastRoute = ExternalOpenRoute.PLEOS_AVD_STOCK
        return try {
            context.startActivity(intent.setComponent(component))
            ExternalOpenResult.INTENT_DISPATCHED
        } catch (_: ActivityNotFoundException) {
            ExternalOpenResult.NO_HANDLER
        } catch (_: SecurityException) {
            ExternalOpenResult.REJECTED
        }
    }
}
