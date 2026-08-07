package com.example.elementannouncebot

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.elementannouncebot.theme.ElementAnnounceBotTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ElementAnnounceBotTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF090A0F)
                ) {
                    AnnounceBotApp()
                }
            }
        }
    }
}

data class Member(val name: String, val userId: String, val status: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnnounceBotApp() {
    var platform by remember { mutableStateOf("Matrix E2EE") }
    var announcementText by remember { mutableStateOf("") }
    var broadcastSuccess by remember { mutableStateOf(false) }

    val members = listOf(
        Member("Kapil Thakare", "@kapilsthakare:matrix.org", "Confirmed ✅"),
        Member("Rohit Jejurkar", "@rohitejejurkar:matrix.org", "Pending ⏳"),
        Member("Samiir Shaiikh", "@samiir9786:matrix.org", "Confirmed ✅"),
        Member("Avani Verekar", "@avaniverekar:matrix.org", "Confirmed ✅"),
        Member("Atharva Chikane", "@atharva_12:matrix.org", "Pending ⏳")
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        // Astryx Top Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Announce Bot Admin",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Text(
                    text = "Meta Astryx Mobile Engine",
                    fontSize = 12.sp,
                    color = Color(0xFFA0AEC0)
                )
            }
            Button(
                onClick = {
                    platform = if (platform == "Matrix E2EE") "Telegram API" else "Matrix E2EE"
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1A1E2D))
            ) {
                Text(text = platform, color = Color(0xFF1877F2), fontSize = 12.sp)
            }
        }

        // Stats Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            StatCard(modifier = Modifier.weight(1f), title = "DELIVERY RATE", value = "100%")
            StatCard(modifier = Modifier.weight(1f), title = "TEAM MEMBERS", value = "21")
        }

        // Broadcast Section
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF12151E)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "NEW BROADCAST STUDIO",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA0AEC0)
                )

                OutlinedTextField(
                    value = announcementText,
                    onValueChange = { announcementText = it },
                    placeholder = { Text("Write announcement text... Use <Name> tag.", color = Color.Gray) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF1877F2),
                        unfocusedBorderColor = Color(0xFF2A2E3D)
                    )
                )

                Button(
                    onClick = {
                        if (announcementText.isNotBlank()) {
                            broadcastSuccess = true
                            announcementText = ""
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1877F2)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(text = "Broadcast to 21 Members", fontWeight = FontWeight.Bold)
                }

                if (broadcastSuccess) {
                    Text(
                        text = "✅ Broadcast sent successfully!",
                        color = Color(0xFF00E676),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Live Tracker List
        Text(
            text = "LIVE CONFIRMATION TRACKER",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFA0AEC0)
        )

        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(members) { member ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF12151E)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(text = member.name, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text(text = member.userId, color = Color.Gray, fontSize = 11.sp)
                        }
                        Text(
                            text = member.status,
                            color = if (member.status.contains("Confirmed")) Color(0xFF00E676) else Color(0xFFFFB300),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun StatCard(modifier: Modifier = Modifier, title: String, value: String) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color(0xFF12151E)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(text = title, fontSize = 11.sp, color = Color(0xFFA0AEC0), fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = value, fontSize = 24.sp, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}
