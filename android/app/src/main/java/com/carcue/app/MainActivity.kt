package com.carcue.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.ViewModelProvider

class MainActivity : ComponentActivity() {
    private lateinit var model: CarCueViewModel
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        model = ViewModelProvider(this)[CarCueViewModel::class.java]
        if (savedInstanceState == null) model.deepLink(intent?.data)
        setContent { CarCueApp(model) }
    }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); model.deepLink(intent.data) }
    override fun onStart() {
        super.onStart()
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueLifecycle", "START")
        model.foreground()
    }
    override fun onStop() {
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueLifecycle", "STOP")
        model.background(); super.onStop()
    }
}
