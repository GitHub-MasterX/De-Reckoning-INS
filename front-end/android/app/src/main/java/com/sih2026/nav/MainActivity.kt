package com.sih2026.nav

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.sih2026.nav.ui.screens.MainScreen
import com.sih2026.nav.ui.theme.SIHNavTheme
import com.sih2026.nav.ui.viewmodel.NavViewModel

/**
 * Two engines behind one map: replays of IO-VNBD blackouts scored offline, and the same round-2 engine running
 * live on this phone's sensors (location permission is asked for when live mode is first chosen).
 */
class MainActivity : ComponentActivity() {

    private val viewModel: NavViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        setContent {
            SIHNavTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(viewModel = viewModel)
                }
            }
        }
    }
}
