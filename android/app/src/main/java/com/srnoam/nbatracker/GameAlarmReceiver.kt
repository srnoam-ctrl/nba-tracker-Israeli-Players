package com.srnoam.nbatracker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class GameAlarmReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_GAME_REMINDER = "com.srnoam.nbatracker.ACTION_GAME_REMINDER"
        const val ACTION_MORNING_DELIVERY = "com.srnoam.nbatracker.ACTION_MORNING_DELIVERY"
        const val ACTION_DAILY_DIGEST = "com.srnoam.nbatracker.ACTION_DAILY_DIGEST"

        const val EXTRA_GAME_TITLE = "extra_game_title"
        const val EXTRA_GAME_DESC = "extra_game_desc"
        const val EXTRA_NOTIFICATION_ID = "extra_notif_id"
        const val EXTRA_PLAYER_ID = "extra_player_id"
    }

    override fun onReceive(context: Context, intent: Intent?) {
        if (intent == null) return

        val helper = NotificationHelper(context)
        val prefs = PreferencesManager(context)

        when (intent.action) {
            ACTION_GAME_REMINDER -> {
                val playerId = intent.getStringExtra(EXTRA_PLAYER_ID) ?: ""
                // Only alert if player is in user's tracking list
                if (playerId.isEmpty() || prefs.isPlayerTracked(playerId)) {
                    val title = intent.getStringExtra(EXTRA_GAME_TITLE) ?: "תזכורת משחק NBA"
                    val desc = intent.getStringExtra(EXTRA_GAME_DESC) ?: "המשחק מתחיל בקרוב!"
                    val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, 2001)

                    helper.showOrQueueNotification(
                        id = notifId,
                        channelId = NotificationHelper.CHANNEL_GAMES,
                        title = title,
                        text = desc,
                        forceNow = false
                    )
                }
            }

            ACTION_MORNING_DELIVERY -> {
                // Deliver any notifications that were delayed during the night
                helper.deliverMorningQueue()
            }

            ACTION_DAILY_DIGEST -> {
                val title = intent.getStringExtra(EXTRA_GAME_TITLE) ?: "🏀 ישראלים ב-NBA היום"
                val desc = intent.getStringExtra(EXTRA_GAME_DESC) ?: "לחץ לפתיחת לוח השידורים המלא"
                val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, 3001)

                helper.showNotificationDirectly(
                    id = notifId,
                    channelId = NotificationHelper.CHANNEL_DAILY,
                    title = title,
                    text = desc
                )
            }
        }
    }
}
