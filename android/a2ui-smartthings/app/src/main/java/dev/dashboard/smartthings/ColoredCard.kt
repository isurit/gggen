package dev.dashboard.smartthings

import androidx.a2ui.compose.runtime.A2uiComponentProperties
import androidx.a2ui.compose.runtime.A2uiComponentScope
import androidx.a2ui.compose.runtime.A2uiComponentState
import androidx.a2ui.compose.runtime.A2uiProperty
import androidx.a2ui.compose.ui.A2uiComponent
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

object ColoredCard : A2uiComponent {
    private val child = A2uiProperty.componentId("child", required = true)
    private val background = A2uiProperty.dynamicString("backgroundColor", required = true)
    override val name = "ColoredCard"
    override val description = "A card with a validated RGB background and an A2UI child."
    override val properties = listOf(child, background)

    @Composable
    override fun A2uiComponentScope.Content(properties: A2uiComponentProperties, modifier: Modifier) {
        val childId = properties[child] ?: return
        val colorText = properties.bind(background) ?: return
        if (!Regex("#[0-9a-fA-F]{6}").matches(colorText)) {
            Text("카드 색상 형식을 확인해 주세요.")
            return
        }
        val color = Color(android.graphics.Color.parseColor(colorText))
        val luminance = 0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue
        val contentColor = if (luminance < 0.55) Color.White else Color.Black
        val state = observeA2uiComponentState(childId)
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = color, contentColor = contentColor),
        ) {
            when (state) {
                is A2uiComponentState.Loading -> LinearProgressIndicator()
                is A2uiComponentState.Error -> Text("카드 렌더링 오류")
                is A2uiComponentState.Success ->
                    A2uiComponent(state.component, Modifier.padding(16.dp))
            }
        }
    }
}
