import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../../feed/domain/post.dart';
import '../../data/history_service.dart';
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
          _HistoryTab(
            loader: () => HistoryService(dio: ref.read(dioProvider))
                .getSentHistory(),
          ),
          _HistoryTab(
            loader: () => HistoryService(dio: ref.read(dioProvider))
                .getReceivedHistory(),
          ),
        ],
      ),
    );
  }
}

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({required this.loader});

  final Future<List<Post>> Function() loader;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Post>>(
      future: loader(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Lỗi: ${snapshot.error}'));
        }
        return HistoryList(posts: snapshot.data ?? []);
      },
    );
  }
}
