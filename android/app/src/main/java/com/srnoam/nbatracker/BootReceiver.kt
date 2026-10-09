package com.srnoam.nbatracker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action == Intent.ACTION_BOOT_COMPLETED ||
            intent?.action == "android.intent.action.QUICKBOOT_POWERON") {
            // Trigger one-time sync worker to reschedule all game alarms
            val syncRequest = OneTimeWorkRequestBuilder<TrackerSyncWorker>().build()
            WorkManager.getInstance(context).enqueue(syncRequest)
        }
    }
}
