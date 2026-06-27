import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/history_service.dart';
import '../../domain/history_item.dart';
import '../widgets/history_list.dart';

/// Displays the user's sent and received photo history (last 24 h).
class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final service = HistoryService(dio: ref.read(dioProvider));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Lịch sử'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Đã gửi'),
            Tab(text: 'Đã nhận'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _SentTab(loader: service.getSentHistory),
          _ReceivedTab(loader: service.getReceivedHistory),
        ],
      ),
    );
  }
}

class _SentTab extends StatelessWidget {
  const _SentTab({required this.loader});

  final Future<List<SentHistoryItem>> Function() loader;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<SentHistoryItem>>(
      future: loader(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Lỗi: ${snapshot.error}'));
        }
        return SentHistoryList(items: snapshot.data ?? []);
      },
    );
  }
}

class _ReceivedTab extends StatelessWidget {
  const _ReceivedTab({required this.loader});

  final Future<List<ReceivedHistoryItem>> Function() loader;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ReceivedHistoryItem>>(
      future: loader(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Lỗi: ${snapshot.error}'));
        }
        return ReceivedHistoryList(items: snapshot.data ?? []);
      },
    );
  }
}
