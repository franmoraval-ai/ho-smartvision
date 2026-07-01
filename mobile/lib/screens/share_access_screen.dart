import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../services/api_client.dart';

/// Permite a un 'owner' compartir acceso (invitar family/viewer) a su cliente.
class ShareAccessScreen extends StatefulWidget {
  const ShareAccessScreen({super.key, required this.clientId});

  final String clientId;

  @override
  State<ShareAccessScreen> createState() => _ShareAccessScreenState();
}

class _ShareAccessScreenState extends State<ShareAccessScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  String _role = 'viewer';
  bool _loading = false;

  late final ApiClient _api = ApiClient(Supabase.instance.client.auth);

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _invite() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await _api.inviteUser(
        email: _email.text.trim(),
        password: _password.text,
        clientId: widget.clientId,
        role: _role,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invitación enviada correctamente.')),
      );
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo invitar: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Compartir acceso')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Invita a familiares o personas de confianza a ver tus cámaras.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email de la persona',
                  prefixIcon: Icon(Icons.mail_outline),
                ),
                validator: (v) =>
                    (v == null || !v.contains('@')) ? 'Email no válido' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Contraseña temporal',
                  prefixIcon: Icon(Icons.lock_outline),
                ),
                validator: (v) =>
                    (v == null || v.length < 6) ? 'Mínimo 6 caracteres' : null,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _role,
                decoration: const InputDecoration(
                  labelText: 'Permiso',
                  prefixIcon: Icon(Icons.shield_outlined),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'viewer',
                    child: Text('Visor (solo ver)'),
                  ),
                  DropdownMenuItem(
                    value: 'family',
                    child: Text('Familiar (solo ver)'),
                  ),
                ],
                onChanged: (v) => setState(() => _role = v ?? 'viewer'),
              ),
              const SizedBox(height: 28),
              FilledButton.icon(
                onPressed: _loading ? null : _invite,
                icon: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
                label: const Text('Enviar invitación'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
