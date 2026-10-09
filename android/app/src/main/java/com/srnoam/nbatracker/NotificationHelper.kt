package com.srnoam.nbatracker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import java.util.Calendar

class NotificationHelper(private val context: Context) {

    private val prefs = PreferencesManager(context)

    companion object {
        const val CHANNEL_GAMES = "channel_nba_games"
        const val CHANNEL_STATS = "channel_nba_stats"
        const val CHANNEL_RECAP = "channel_nba_recap"
        const val CHANNEL_DAILY = "channel_nba_daily"
    }

    init {
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

            val gamesChannel = NotificationChannel(
                CHANNEL_GAMES,
                context.getString(R.string.channel_games_name),
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = context.getString(R.string.channel_games_desc)
                enableVibration(true)
            }

            val statsChannel = NotificationChannel(
                CHANNEL_STATS,
                context.getString(R.string.channel_stats_name),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = context.getString(R.string.channel_stats_desc)
            }

            val recapChannel = NotificationChannel(
                CHANNEL_RECAP,
                context.getString(R.string.channel_recap_name),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = context.getString(R.string.channel_recap_desc)
            }

            val dailyChannel = NotificationChannel(
                CHANNEL_DAILY,
                context.getString(R.string.channel_daily_name),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = context.getString(R.string.channel_daily_desc)
            }

            nm.createNotificationChannels(listOf(gamesChannel, statsChannel, recapChannel, dailyChannel))
        }
    }

    /**
     * Checks if current hour is in user's quiet hours (e.g. 23:00 - 07:00).
     */
    fun isQuietHourNow(): Boolean {
        if (!prefs.isQuietHoursEnabled) return false
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        val start = prefs.quietStartHour
        val end = prefs.quietEndHour

        return if (start > end) {
            hour >= start || hour < end
        } else {
            hour in start until end
        }
    }

    /**
     * Shows notification or queues it for morning delivery if it's currently night time.
     */
    fun showOrQueueNotification(
        id: Int,
        channelId: String,
        title: String,
        text: String,
        urlToOpen: String? = null,
        forceNow: Boolean = false
    ) {
        if (!forceNow && isQuietHourNow()) {
            // Queue for morning delivery to avoid waking the user
            val payload = "{\"id\":$id,\"channel\":\"$channelId\",\"title\":\"$title\",\"text\":\"$text\",\"url\":\"$urlToOpen\"}"
            prefs.queueNotification(payload)
            return
        }

        showNotificationDirectly(id, channelId, title, text, urlToOpen)
    }

    fun showNotificationDirectly(
        id: Int,
        channelId: String,
        title: String,
        text: String,
        urlToOpen: String? = null
    ) {
        val launchIntent = if (urlToOpen != null && urlToOpen.startsWith("http")) {
            Intent(Intent.ACTION_VIEW, Uri.parse(urlToOpen))
        } else {
            Intent(context, MainActivity::class.java)
        }.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            id,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)

        try {
            NotificationManagerCompat.from(context).notify(id, builder.build())
        } catch (_: SecurityException) {
            // Permission not granted by user
        }
    }

    /**
     * Delivers queued morning notifications at 07:00 / 08:00 AM.
     */
    fun deliverMorningQueue() {
        val queued = prefs.popQueuedNotifications()
        queued.forEachIndexed { idx, raw ->
            try {
                val obj = org.json.JSONObject(raw)
                val id = obj.optInt("id", 1000 + idx)
                val channel = obj.optString("channel", CHANNEL_STATS)
                val title = obj.optString("title", "עדכון NBA")
                val text = obj.optString("text", "")
                val url = obj.optString("url", null)

                showNotificationDirectly(id, channel, "☀️ $title", text, url)
            } catch (_: Exception) {}
        }
    }
}
