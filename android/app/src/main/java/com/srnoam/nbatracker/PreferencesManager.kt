package com.srnoam.nbatracker

import android.content.Context
import android.content.SharedPreferences

/**
 * Manages local user preferences with zero external tracking:
 * - Selective player tracking
 * - Quiet hours & night-time delay delivery
 * - Daily morning digest time
 */
class PreferencesManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("nba_tracker_prefs", Context.MODE_PRIVATE)

    companion object {
        const val PREF_TRACK_DENI = "track_deni_avdija"
        const val PREF_TRACK_BEN = "track_ben_saraf"
        const val PREF_TRACK_WOLF = "track_danny_wolf"
        const val PREF_TRACK_SHARP = "track_emanuel_sharp"

        const val PREF_QUIET_HOURS_ENABLED = "quiet_hours_enabled"
        const val PREF_QUIET_START_HOUR = "quiet_start_hour" // Default 23 (23:00)
        const val PREF_QUIET_END_HOUR = "quiet_end_hour"     // Default 7 (07:00)
        const val PREF_MORNING_HOUR = "morning_hour"         // Default 7 (07:30)

        const val PREF_DAILY_DIGEST_ENABLED = "daily_digest_enabled"
        const val PREF_DAILY_DIGEST_HOUR = "daily_digest_hour" // Default 8 (08:00)
        const val PREF_REMINDER_LEAD_MINS = "reminder_lead_mins" // Default 30 mins before game

        const val PREF_LAST_ETAG = "last_etag"
        const val PREF_QUEUED_NOTIFICATIONS = "queued_notifications"
    }

    // Player tracking checks
    fun isPlayerTracked(playerId: String): Boolean {
        return when (playerId) {
            "deni_avdija" -> prefs.getBoolean(PREF_TRACK_DENI, true)
            "ben_saraf" -> prefs.getBoolean(PREF_TRACK_BEN, true)
            "danny_wolf" -> prefs.getBoolean(PREF_TRACK_WOLF, true)
            "emanuel_sharp" -> prefs.getBoolean(PREF_TRACK_SHARP, true)
            else -> true
        }
    }

    fun setPlayerTracked(playerId: String, enabled: Boolean) {
        val key = when (playerId) {
            "deni_avdija" -> PREF_TRACK_DENI
            "ben_saraf" -> PREF_TRACK_BEN
            "danny_wolf" -> PREF_TRACK_WOLF
            "emanuel_sharp" -> PREF_TRACK_SHARP
            else -> return
        }
        prefs.edit().putBoolean(key, enabled).apply()
    }

    // Quiet Hours / Night settings
    val isQuietHoursEnabled: Boolean
        get() = prefs.getBoolean(PREF_QUIET_HOURS_ENABLED, true)

    val quietStartHour: Int
        get() = prefs.getInt(PREF_QUIET_START_HOUR, 23)

    val quietEndHour: Int
        get() = prefs.getInt(PREF_QUIET_END_HOUR, 7)

    val morningDeliveryHour: Int
        get() = prefs.getInt(PREF_MORNING_HOUR, 7)

    // Daily Digest
    val isDailyDigestEnabled: Boolean
        get() = prefs.getBoolean(PREF_DAILY_DIGEST_ENABLED, true)

    val dailyDigestHour: Int
        get() = prefs.getInt(PREF_DAILY_DIGEST_HOUR, 8)

    val leadTimeMinutes: Int
        get() = prefs.getInt(PREF_REMINDER_LEAD_MINS, 30)

    // ETag caching
    var lastETag: String?
        get() = prefs.getString(PREF_LAST_ETAG, null)
        set(value) = prefs.edit().putString(PREF_LAST_ETAG, value).apply()

    // Queued night notifications
    fun queueNotification(jsonStr: String) {
        val current = prefs.getStringSet(PREF_QUEUED_NOTIFICATIONS, mutableSetOf()) ?: mutableSetOf()
        val updated = current.toMutableSet()
        updated.add(jsonStr)
        prefs.edit().putStringSet(PREF_QUEUED_NOTIFICATIONS, updated).apply()
    }

    fun popQueuedNotifications(): List<String> {
        val current = prefs.getStringSet(PREF_QUEUED_NOTIFICATIONS, mutableSetOf()) ?: emptySet()
        prefs.edit().remove(PREF_QUEUED_NOTIFICATIONS).apply()
        return current.toList()
    }
}
