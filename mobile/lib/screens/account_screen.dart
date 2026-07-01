import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../services/supabase_service.dart';

/// Pestaña de Cuenta: perfil del usuario, acciones y cierre de sesión.
class AccountScreen extends StatelessWidget {
  const AccountScreen({
    super.key,
    required this.service,
    required this.onShare,
    required this.onSignOut,
  });

  final SupabaseService service;
  final VoidCallback onShare;
  final Future<void> Function() onSignOut;

  @override
  Widget build(BuildContext context) {
    final email = service.user?.email ?? '—';
    final initial = email.isNotEmpty ? email[0].toUpperCase() : '?';

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _ProfileHeader(email: email, initial: initial),
        const SizedBox(height: 24),
        Card(
          margin: EdgeInsets.zero,
          child: Column(
            children: [
              _Tile(
                icon: Icons.person_add_alt_1_rounded,
                title: 'Compartir acceso',
                subtitle: 'Invita a familiares o vigilantes',
                onTap: onShare,
              ),
              const Divider(height: 1),
              _Tile(
                icon: Icons.notifications_rounded,
                title: 'Notificaciones',
                subtitle: 'Alertas de movimiento y personas',
                onTap: () => _showInfo(
                  context,
                  'Notificaciones',
                  'Recibes alertas push cuando tus cámaras detectan '
                      'movimiento o personas. Actívalas en los ajustes del '
                      'teléfono si no las ves.',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Card(
          margin: EdgeInsets.zero,
          child: Column(
            children: [
              _Tile(
                icon: Icons.shield_outlined,
                title: 'Privacidad y seguridad',
                subtitle: 'Cómo protegemos tus cámaras',
                onTap: () => _showInfo(
                  context,
                  'Privacidad y seguridad',
                  'Tus datos y cámaras están protegidos: cada usuario solo '
                      'puede ver la información de su propia cuenta. Las '
                      'credenciales de las cámaras nunca salen del sistema.',
                ),
              ),
              const Divider(height: 1),
              _Tile(
                icon: Icons.help_outline_rounded,
                title: 'Ayuda y soporte',
                subtitle: 'Preguntas frecuentes y contacto',
                onTap: () => _showInfo(
                  context,
                  'Ayuda y soporte',
                  'Si necesitas ayuda con tus cámaras o tu cuenta, contacta '
                      'a tu proveedor de Ho smartvision.',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () => _confirmSignOut(context),
          icon: const Icon(Icons.logout_rounded),
          label: const Text('Cerrar sesión'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            foregroundColor: Theme.of(context).colorScheme.error,
            side: BorderSide(
              color: Theme.of(context).colorScheme.error.withValues(alpha: 0.5),
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: Text(
            'Ho smartvision',
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
              fontSize: 12,
            ),
          ),
        ),
      ],
    );
  }

  void _showInfo(BuildContext context, String title, String body) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Entendido'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmSignOut(BuildContext context) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Cerrar sesión'),
        content: const Text('¿Seguro que quieres cerrar sesión?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Cerrar sesión'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await onSignOut();
    }
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.email, required this.initial});

  final String email;
  final String initial;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppTheme.brandLinearGradient,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: Colors.white,
            child: Text(
              initial,
              style: const TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.w800,
                color: Color(0xFF5B5BF6),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Mi cuenta',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  email,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListTile(
      onTap: onTap,
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: scheme.primaryContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: scheme.onPrimaryContainer, size: 22),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right_rounded),
    );
  }
}
