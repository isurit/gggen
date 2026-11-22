package dev.dashboard.smartthings

import androidx.a2ui.compose.runtime.A2uiComponentProperties
import androidx.a2ui.compose.runtime.A2uiComponentScope
import androidx.a2ui.compose.runtime.A2uiComponentState
import androidx.a2ui.compose.runtime.A2uiProperty
import androidx.a2ui.compose.ui.A2uiComponent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

/** Presents two server-defined A2UI child trees with native paging gestures. */
object AirCarePager : A2uiComponent {
    private val title = A2uiProperty.dynamicString("title", required = true)
    private val subtitle = A2uiProperty.dynamicString("subtitle", required = true)
    private val firstPage = A2uiProperty.componentId("firstPage", required = true)
    private val secondPage = A2uiProperty.componentId("secondPage", required = true)

    override val name = "AirCarePager"
    override val description = "A two-page air care card with swipe and page controls."
    override val properties = listOf(title, subtitle, firstPage, secondPage)

    @Composable
    override fun A2uiComponentScope.Content(properties: A2uiComponentProperties, modifier: Modifier) {
        val heading = properties.bind(title) ?: return
        val description = properties.bind(subtitle) ?: return
        val first = properties[firstPage] ?: return
        val second = properties[secondPage] ?: return
        val pages = listOf(first, second)
        val pager = rememberPagerState { pages.size }
        val scope = rememberCoroutineScope()
        val accent = Color(0xFF006653)

        Card(
            modifier = modifier.fillMaxWidth(),
            shape = RoundedCornerShape(26.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xFFEDF4F1),
                contentColor = Color(0xFF173632),
            ),
        ) {
            Column(
                Modifier.fillMaxWidth().padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(heading, style = MaterialTheme.typography.titleLarge)
                    Text("${pager.currentPage + 1} / ${pages.size}", color = accent)
                }
                Text(description, style = MaterialTheme.typography.bodyMedium)
                HorizontalPager(
                    state = pager,
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.Top,
                ) { page ->
                    val state = observeA2uiComponentState(pages[page])
                    Box(Modifier.fillMaxWidth().padding(vertical = 12.dp)) {
                        when (state) {
                            is A2uiComponentState.Loading -> LinearProgressIndicator(Modifier.fillMaxWidth())
                            is A2uiComponentState.Error -> Text("페이지를 표시할 수 없습니다.")
                            is A2uiComponentState.Success -> A2uiComponent(state.component, Modifier.fillMaxWidth())
                        }
                    }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                    pages.indices.forEach { page ->
                        val active = page == pager.currentPage
                        TextButton(
                            onClick = { scope.launch { pager.animateScrollToPage(page) } },
                            modifier = Modifier.semantics {
                                contentDescription = "${page + 1}페이지"
                                selected = active
                            },
                        ) {
                            Box(Modifier.size(8.dp).background(
                                if (active) accent else Color(0xFF899F98), CircleShape,
                            ))
                        }
                    }
                }
            }
        }
    }
}
