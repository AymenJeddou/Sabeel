import 'dart:async';

import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../models/remote_report.dart';
import '../services/api_client.dart';

/// Chat with the municipality / DGPC agents. Messages land in the dashboard's
/// Messages inbox; replies are polled every few seconds while this is open.
class SupportChatScreen extends StatefulWidget {
  const SupportChatScreen({
    super.key,
    this.initialText = '',
    this.api = const RoadScanApiClient(),
  });

  /// Pre-filled draft, e.g. "À propos de TN-1A2B : " from a report card.
  final String initialText;
  final RoadScanApiClient api;

  @override
  State<SupportChatScreen> createState() => _SupportChatScreenState();
}

class _SupportChatScreenState extends State<SupportChatScreen> {
  static const _suggestions = [
    'Où en est mon signalement ?',
    'Le nid-de-poule est dangereux, pouvez-vous intervenir vite ?',
    "J'ai signalé une erreur (pas un nid-de-poule).",
  ];

  late final _draft = TextEditingController(text: widget.initialText);
  final _scroll = ScrollController();
  List<ChatMessage>? _messages;
  String? _error;
  bool _sending = false;
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _poll?.cancel();
    _draft.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final messages = await widget.api.fetchMessages();
      if (!mounted) return;
      final grew = messages.length != (_messages?.length ?? 0);
      setState(() {
        _messages = messages;
        _error = null;
      });
      if (grew) _scrollToEnd();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  void _scrollToEnd() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }
  });

  Future<void> _send([String? text]) async {
    final body = (text ?? _draft.text).trim();
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      await widget.api.sendMessage(body);
      _draft.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final messages = _messages;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: const Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: Color(0x1F0F6E6A),
              child: Icon(Icons.support_agent, color: sabeelTeal, size: 20),
            ),
            SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Assistance Sabeel',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
                Text(
                  'Municipalité · DGPC',
                  style: TextStyle(fontSize: 12, color: sabeelMuted),
                ),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          if (_error != null && messages == null)
            Expanded(
              child: _Notice(
                icon: Icons.cloud_off,
                text: 'Serveur injoignable.\nVérifie ta connexion.',
              ),
            )
          else if (messages == null)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (messages.isEmpty)
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const _Notice(
                    icon: Icons.forum_outlined,
                    text:
                        'Une question sur un signalement ?\nLes services techniques te répondent ici.',
                  ),
                  const SizedBox(height: 16),
                  for (final s in _suggestions)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: OutlinedButton(
                        onPressed: () => _draft.text = s,
                        style: OutlinedButton.styleFrom(
                          alignment: Alignment.centerLeft,
                          padding: const EdgeInsets.all(14),
                          side: const BorderSide(color: sabeelLine),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        child: Text(
                          s,
                          style: const TextStyle(color: sabeelInk),
                        ),
                      ),
                    ),
                ],
              ),
            )
          else
            Expanded(
              child: ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                itemCount: messages.length,
                itemBuilder: (_, i) => _Bubble(message: messages[i]),
              ),
            ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _draft,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      decoration: InputDecoration(
                        hintText: 'Écrire un message…',
                        filled: true,
                        fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                          borderSide: const BorderSide(color: sabeelLine),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                          borderSide: const BorderSide(color: sabeelLine),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ? null : _send,
                    style: IconButton.styleFrom(
                      backgroundColor: sabeelNavy,
                      minimumSize: const Size(48, 48),
                    ),
                    icon: const Icon(Icons.send_rounded, color: Colors.white),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final mine = message.fromCitizen;
    final t = message.createdAt.toLocal();
    final time =
        '${t.day}/${t.month} ${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.78,
        ),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
        decoration: BoxDecoration(
          color: mine ? sabeelNavy : Colors.white,
          border: mine ? null : Border.all(color: sabeelLine),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(18),
            topRight: const Radius.circular(18),
            bottomLeft: Radius.circular(mine ? 18 : 4),
            bottomRight: Radius.circular(mine ? 4 : 18),
          ),
        ),
        child: Column(
          crossAxisAlignment: mine
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            Text(
              message.body,
              style: TextStyle(
                color: mine ? Colors.white : sabeelInk,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              time,
              style: TextStyle(
                fontSize: 10,
                color: mine ? Colors.white60 : sabeelMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 44, color: sabeelMuted.withValues(alpha: 0.6)),
          const SizedBox(height: 10),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(color: sabeelMuted),
          ),
        ],
      ),
    );
  }
}
