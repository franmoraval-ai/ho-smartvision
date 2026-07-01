import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config/env.dart';
import 'config/theme.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Datos de formato de fecha en español (para los timelines de eventos).
  Intl.defaultLocale = 'es';
  await initializeDateFormatting('es');

  if (Env.isConfigured) {
    await Supabase.initialize(
      url: Env.supabaseUrl,
      // `publishableKey` reemplaza a `anonKey` (acepta la anon/publishable key).
      publishableKey: Env.supabaseAnonKey,
    );
  }

  runApp(const HoSmartvisionApp());
}

class HoSmartvisionApp extends StatelessWidget {
  const HoSmartvisionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ho smartvision',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: const _Root(),
    );
  }
}

/// Decide qué pantalla mostrar según el estado de autenticación.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    if (!Env.isConfigured) {
      return const _ConfigError();
    }

    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        final session = Supabase.instance.client.auth.currentSession;
        if (session == null) {
          return const LoginScreen();
        }
        return const HomeScreen();
      },
    );
  }
}

class _ConfigError extends StatelessWidget {
  const _ConfigError();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: const [
              Icon(Icons.settings, size: 48),
              SizedBox(height: 12),
              Text(
                'Configuración incompleta',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Ejecuta la app con --dart-define=SUPABASE_URL=... y '
                '--dart-define=SUPABASE_ANON_KEY=...',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
