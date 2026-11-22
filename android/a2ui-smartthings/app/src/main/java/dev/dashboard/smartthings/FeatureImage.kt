package dev.dashboard.smartthings

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI

private const val FEATURE_IMAGE_URL = "https://picsum.photos/200/300"

@Composable
internal fun FeatureImage(url: String, description: String?, contentScale: ContentScale) {
    val bitmap by produceState<Bitmap?>(null, url) {
        value = withContext(Dispatchers.IO) {
            try {
                loadFeatureImage(url)
            } catch (_: IOException) {
                null
            }
        }
    }
    Box(
        Modifier.padding(end = 12.dp).size(width = 104.dp, height = 156.dp)
            .clip(RoundedCornerShape(12.dp)),
        contentAlignment = Alignment.Center,
    ) {
        val downloaded = bitmap
        if (downloaded != null) {
            Image(
                downloaded.asImageBitmap(),
                contentDescription = description,
                modifier = Modifier.matchParentSize(),
                contentScale = contentScale,
            )
        } else if (url == FEATURE_IMAGE_URL) {
            Image(
                painter = painterResource(R.drawable.feature_suggestion_photo),
                contentDescription = description,
                modifier = Modifier.matchParentSize(),
                contentScale = contentScale,
            )
        }
    }
}

private fun loadFeatureImage(url: String): Bitmap {
    if (url != FEATURE_IMAGE_URL) throw IOException("지원하는 이미지 주소를 확인해 주세요.")
    var uri = URI(url)
    repeat(3) {
        if (uri.scheme != "https" || uri.userInfo != null || uri.port != -1 ||
            uri.host !in setOf("picsum.photos", "fastly.picsum.photos")
        ) throw IOException("지원하는 이미지 주소를 확인해 주세요.")
        val connection = uri.toURL().openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 8_000
            connection.readTimeout = 8_000
            when (connection.responseCode) {
                in 200..299 -> {
                    val maxBytes = 512 * 1024
                    val bytes = connection.inputStream.use { stream ->
                        val data = java.io.ByteArrayOutputStream()
                        val buffer = ByteArray(8192)
                        while (true) {
                            val count = stream.read(buffer)
                            if (count < 0) break
                            if (data.size() + count > maxBytes) throw IOException("이미지가 너무 큽니다.")
                            data.write(buffer, 0, count)
                        }
                        data.toByteArray()
                    }
                    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
                    if (bounds.outWidth !in 1..1024 || bounds.outHeight !in 1..1024) {
                        throw IOException("이미지 크기를 확인해 주세요.")
                    }
                    return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        ?: throw IOException("이미지 형식을 확인해 주세요.")
                }
                in 300..399 -> {
                    val location = connection.getHeaderField("Location")
                        ?: throw IOException("이미지 이동 주소가 없습니다.")
                    uri = try {
                        uri.resolve(location)
                    } catch (error: IllegalArgumentException) {
                        throw IOException("이미지 이동 주소가 올바르지 않습니다.", error)
                    }
                }
                else -> throw IOException("이미지를 불러오지 못했습니다.")
            }
        } finally {
            connection.disconnect()
        }
    }
    throw IOException("이미지 이동 횟수를 초과했습니다.")
}
