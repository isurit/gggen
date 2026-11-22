package dev.dashboard.smartthings

import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.a2ui.compose.runtime.A2uiMessageParser
import androidx.a2ui.compose.ui.A2uiCatalog
import androidx.a2ui.compose.ui.A2uiMessageProcessor
import androidx.a2ui.compose.ui.catalog.A2uiBasicCatalogV1
import androidx.a2ui.model.catalog.functions.A2uiLocaleProvider
import androidx.a2ui.model.processor.A2uiSurfaceModel
import androidx.a2ui.model.processor.processInput
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.material3.a2ui.A2uiSurface
import androidx.compose.material3.a2ui.catalog.MaterialA2uiBasicCatalogV1Defaults
import androidx.compose.material3.a2ui.catalog.materialA2uiBasicCatalogV1
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = true
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightNavigationBars = true
        intent.getStringExtra("appKey")?.let { pairingKey ->
            getSharedPreferences("connection", 0).edit().putString("key", pairingKey).apply()
            intent.removeExtra("appKey")
        }
        setContent { MaterialTheme { DeviceScreen() } }
    }
}

class DevicesViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences("connection", 0)
    val apiUrl = MutableStateFlow(preferences.getString("url", BuildConfig.API_URL) ?: BuildConfig.API_URL)
    val appKey = MutableStateFlow(preferences.getString("key", BuildConfig.APP_KEY) ?: BuildConfig.APP_KEY)
    val busy = MutableStateFlow(false)
    val status = MutableStateFlow("대시보드에서 설정을 저장한 뒤 새로고침하세요.")
    private val catalog = materialA2uiBasicCatalogV1(
        image = MaterialA2uiBasicCatalogV1Defaults.image { url, description, contentScale, _, _ ->
            FeatureImage(url, description, contentScale)
        },
        video = MaterialA2uiBasicCatalogV1Defaults.video { _, _, _ -> },
        audioPlayer = MaterialA2uiBasicCatalogV1Defaults.audioPlayer { _, _, _, _ -> },
        functions = A2uiBasicCatalogV1.Functions(application, A2uiLocaleProvider.Default),
    )
    private val deviceCatalog = A2uiCatalog(
        catalogId = "urn:gggen:device-catalog:v1",
        components = catalog.components + listOf(ColoredCard, AirCarePager, FeatureSuggestionCard),
        functions = catalog.functions,
        themeSchema = catalog.themeSchema,
    )
    private val parser = A2uiMessageParser()
    val surfaces = MutableStateFlow<List<A2uiSurfaceModel>>(emptyList())
    private var renderJob: Job? = null

    fun refresh() {
        if (busy.value) return
        busy.value = true
        viewModelScope.launch {
            status.value = "화면을 불러오고 있습니다."
            try {
                val response = withContext(Dispatchers.IO) { fetchScreen() }
                val messages = response.getJSONArray("messages")
                require(messages.length() == 3) { "서버의 화면 메시지를 확인해 주세요." }
                // Retired models stay intact until Compose releases them. Clearing their
                // properties through deleteSurface can race with an outgoing animation.
                val processor = A2uiMessageProcessor(catalogs = listOf(catalog, deviceCatalog))
                renderJob?.cancel()
                renderJob = viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
                    launch(Dispatchers.Default) { processor.collectMessages() }
                    launch(start = CoroutineStart.UNDISPATCHED) {
                        processor.outboundEvents.collect { _ -> }
                    }
                    processor.activeSurfaces.collect { surfaces.value = it }
                }
                for (i in 0 until messages.length()) {
                    processor.processInput(parser, messages.getJSONObject(i).toString())
                }
                preferences.edit().putString("url", apiUrl.value).putString("key", appKey.value).apply()
                val meta = response.getJSONObject("meta")
                status.value = if (meta.optString("dataSource") == "sample") {
                    if (meta.optString("figmaSampleId") == "4") "기능 제안" else "에어 케어 · 예시 데이터"
                } else {
                    "기기 ${meta.getInt("deviceCount")}개 · 설정 ${meta.getInt("revision")} · " +
                        if (meta.getBoolean("layoutCached")) "배치 재사용" else "새 배치 생성"
                }
            } catch (error: Exception) {
                status.value = error.message ?: "서버에 연결할 수 없습니다."
            } finally {
                busy.value = false
            }
        }
    }

    private fun fetchScreen(): JSONObject {
        val uri = URI(apiUrl.value.trim())
        require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null) {
            "HTTPS API 주소를 입력해 주세요."
        }
        val connection = uri.toURL().openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 15_000
            connection.readTimeout = 100_000
            connection.setRequestProperty("Authorization", "Bearer " + appKey.value.trim())
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("X-A2UI-Feature-Suggestion", "1")
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader()?.use { it.readText() }
                ?: throw IllegalStateException("서버 응답이 비어 있습니다.")
            val response = JSONObject(body)
            check(code in 200..299 && response.optBoolean("ok")) {
                response.optString("error", "API 요청 실패 ($code)")
            }
            return response
        } finally {
            connection.disconnect()
        }
    }
}

@Composable
fun DeviceScreen(vm: DevicesViewModel = viewModel()) {
    val surfaces by vm.surfaces.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val url by vm.apiUrl.collectAsStateWithLifecycle()
    val connectionKey by vm.appKey.collectAsStateWithLifecycle()
    var showConnection by remember { mutableStateOf(false) }
    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing).padding(20.dp)) {
            Text("SmartThings", style = MaterialTheme.typography.headlineMedium)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = vm::refresh, enabled = !busy) { Text(if (busy) "조회 중…" else "새로고침") }
                TextButton(onClick = { showConnection = !showConnection }) { Text("연결 설정") }
            }
            if (showConnection) {
                OutlinedTextField(value = url, onValueChange = { vm.apiUrl.value = it },
                    label = { Text("HTTPS API 주소") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(value = connectionKey, onValueChange = { vm.appKey.value = it },
                    label = { Text("앱 연결 키") }, modifier = Modifier.fillMaxWidth(),
                    visualTransformation = PasswordVisualTransformation(), singleLine = true)
            }
            Text(status, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 12.dp))
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            // The A2UI List owns scrolling. It receives a bounded viewport here.
            Column(Modifier.fillMaxWidth().weight(1f)) {
                surfaces.forEach { surface ->
                    key(surface.id) {
                        A2uiSurface(surfaceModel = surface, modifier = Modifier.fillMaxSize(),
                            errorContent = { Text("화면 렌더링 오류 · ${it.message}") })
                    }
                }
            }
        }
    }
}
