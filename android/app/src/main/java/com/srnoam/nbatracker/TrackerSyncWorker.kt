package com.srnoam.nbatracker

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.TimeUnit

class TrackerSyncWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val prefs = PreferencesManager(context)
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    companion object {
        const val DATA_URL = "https://raw.githubusercontent.com/srnoam-ctrl/nba-tracker-Israeli-Players/main/data/games.json"
    }

    override suspend fun doWork(): Result {
        return try {
            val reqBuilder = Request.Builder().url(DATA_URL)
            prefs.lastETag?.let { reqBuilder.header("If-None-Match", it) }

            val response = client.newCall(reqBuilder.build()).execute()

            if (response.code == 304) {
                // Not modified, zero bytes downloaded!
                return Result.success()
            }

            if (!response.isSuccessful) {
                return Result.retry()
            }

            val etag = response.header("ETag")
            if (etag != null) {
                prefs.lastETag = etag
            }

            val body = response.body?.string() ?: return Result.success()
            parseAndScheduleAlarms(body)

            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    private fun parseAndScheduleAlarms(jsonString: String) {
        val root = JSONObject(jsonString)
        val allGames = root.optJSONArray("all_games") ?: return
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }

        val nowMs = System.currentTimeMillis()
        val leadMs = prefs.leadTimeMinutes * 60 * 1000L

        for (i in 0 until allGames.length()) {
            val g = allGames.getJSONObject(i)
            if (g.optBoolean("is_completed", false)) continue

            val utcDateStr = g.optString("utc_date", "")
            if (utcDateStr.isEmpty()) continue

            val gameDate = try {
                isoFormat.parse(utcDateStr)
            } catch (_: Exception) {
                null
            } ?: continue

            val gameTimeMs = gameDate.time
            val reminderTimeMs = gameTimeMs - leadMs

            // Only schedule if in future
            if (reminderTimeMs > nowMs) {
                val gameId = g.optString("id", i.toString()).hashCode()
                val away = g.optJSONObject("away_team")?.optString("name") ?: ""
                val home = g.optJSONObject("home_team")?.optString("name") ?: ""
                val timeIl = g.optString("time_il", "")
                val channel = g.optJSONObject("tv_broadcast")?.optString("channel_name") ?: "שידור טרם נקבע"

                val playersArr = g.optJSONArray("players")
                val firstPlayerId = playersArr?.optJSONObject(0)?.optString("id") ?: ""
                val playerNames = (0 until (playersArr?.length() ?: 0))
                    .mapNotNull { playersArr?.optJSONObject(it)?.optString("name_he") }
                    .joinToString(", ")

                val title = "🏀 $playerNames משחקים ב-$timeIl!"
                val desc = "$away נגד $home • ערוץ: $channel"

                val intent = Intent(context, GameAlarmReceiver::class.java).apply {
                    action = GameAlarmReceiver.ACTION_GAME_REMINDER
                    putExtra(GameAlarmReceiver.EXTRA_GAME_TITLE, title)
                    putExtra(GameAlarmReceiver.EXTRA_GAME_DESC, desc)
                    putExtra(GameAlarmReceiver.EXTRA_PLAYER_ID, firstPlayerId)
                    putExtra(GameAlarmReceiver.EXTRA_NOTIFICATION_ID, gameId)
                }

                val pi = PendingIntent.getBroadcast(
                    context,
                    gameId,
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, reminderTimeMs, pi)
                } else {
                    alarmManager.set(AlarmManager.RTC_WAKEUP, reminderTimeMs, pi)
                }
            }
        }

        // Schedule Daily Morning/Evening Digest
        scheduleDailyDigest(alarmManager)
    }

    private fun scheduleDailyDigest(alarmManager: AlarmManager) {
        if (!prefs.isDailyDigestEnabled) return

        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, prefs.dailyDigestHour)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            if (before(Calendar.getInstance())) {
                add(Calendar.DAY_OF_YEAR, 1)
            }
        }

        val intent = Intent(context, GameAlarmReceiver::class.java).apply {
            action = GameAlarmReceiver.ACTION_DAILY_DIGEST
            putExtra(GameAlarmReceiver.EXTRA_GAME_TITLE, "🏀 סיכום משחקי ישראלים ב-NBA היום")
            putExtra(GameAlarmReceiver.EXTRA_GAME_DESC, "לחץ כאן לפתיחת לוח השידורים המלא")
            putExtra(GameAlarmReceiver.EXTRA_NOTIFICATION_ID, 9999)
        }

        val pi = PendingIntent.getBroadcast(
            context,
            9999,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        alarmManager.setInexactRepeating(
            AlarmManager.RTC,
            calendar.timeInMillis,
            AlarmManager.INTERVAL_DAY,
            pi
        )
    }
}
