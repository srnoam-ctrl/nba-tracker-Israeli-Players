package com.srnoam.nbatracker

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.ProgressBar
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var prefs: PreferencesManager

    companion object {
        const val DASHBOARD_URL = "https://srnoam-ctrl.github.io/nba-tracker-Israeli-Players/"
    }

    private val requestNotificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            if (isGranted) {
                // Initialize background sync and alarms immediately
                enqueueInitialSync()
            }
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        prefs = PreferencesManager(this)

        // Request Android 13+ Notification permission
        checkNotificationPermission()

        // Schedule battery-efficient periodic background sync (every 12 hours, battery not low)
        schedulePeriodicSync()

        // Setup UI Layout
        val rootLayout = FrameLayout(this).apply {
            setBackgroundColor(ContextCompat.getColor(this@MainActivity, R.color.bg_dark))
        }

        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(ContextCompat.getColor(this@MainActivity, R.color.bg_dark))
        }

        progressBar = ProgressBar(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.CENTER
            }
            visibility = View.VISIBLE
        }

        rootLayout.addView(webView)
        rootLayout.addView(progressBar)
        setContentView(rootLayout)

        configureWebView()
        webView.loadUrl(DASHBOARD_URL)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        settings.setSupportZoom(false)

        // Security Hardening: Disallow local file schemes
        settings.allowFileAccess = false
        settings.allowContentAccess = false

        // Bridge to allow web app to read/write notification preferences
        webView.addJavascriptInterface(WebAppInterface(this, prefs), "AndroidBridge")

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                progressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                progressBar.visibility = View.GONE
            }

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url?.toString() ?: return false

                // Intercept YouTube links to open directly in the official YouTube App
                if (url.contains("youtube.com") || url.contains("youtu.be")) {
                    try {
                        val ytIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                            setPackage("com.google.android.youtube")
                        }
                        startActivity(ytIntent)
                        return true
                    } catch (_: Exception) {
                        val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                        startActivity(browserIntent)
                        return true
                    }
                }

                // Keep app navigation inside dashboard
                if (url.startsWith("https://srnoam-ctrl.github.io/")) {
                    return false
                }

                // External links open in browser
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                startActivity(intent)
                return true
            }
        }
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                enqueueInitialSync()
            }
        } else {
            enqueueInitialSync()
        }
    }

    private fun enqueueInitialSync() {
        val initialRequest = OneTimeWorkRequestBuilder<TrackerSyncWorker>().build()
        WorkManager.getInstance(this).enqueue(initialRequest)
    }

    private fun schedulePeriodicSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()

        val periodicSync = PeriodicWorkRequestBuilder<TrackerSyncWorker>(
            12, TimeUnit.HOURS,
            1, TimeUnit.HOURS // Flex interval
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "nba_tracker_sync_work",
            ExistingPeriodicWorkPolicy.KEEP,
            periodicSync
        )
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    // JavaScript Bridge class for Web to Android communication
    class WebAppInterface(private val activity: MainActivity, private val prefs: PreferencesManager) {
        @JavascriptInterface
        fun isPlayerTracked(playerId: String): Boolean {
            return prefs.isPlayerTracked(playerId)
        }

        @JavascriptInterface
        fun setPlayerTracked(playerId: String, enabled: Boolean) {
            prefs.setPlayerTracked(playerId, enabled)
        }

        @JavascriptInterface
        fun isQuietHoursEnabled(): Boolean {
            return prefs.isQuietHoursEnabled
        }

        @JavascriptInterface
        fun triggerSyncNow() {
            activity.enqueueInitialSync()
        }
    }
}
