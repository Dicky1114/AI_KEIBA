"""
@file    dashboard_view.py
@brief   ダッシュボード画面 — DB実データ + 馬券シミュレーション
@version 2.0.0  2026-03-30  DB実データ化 + シミュレーション対応 (Dicky1114)
"""

import json
from django.views import View
from django.shortcuts import render
# LoginRequiredMixin removed — シングルユーザーモード
from django.db.models import Sum, Count, Q, Avg, F, ExpressionWrapper, FloatField
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from datetime import timedelta
import logging

from ..models import BettingRecord, TrainingInfo

logger = logging.getLogger(__name__)


def _build_stats(qs):
    """
    BettingRecord QuerySet から集計統計を構築する。
    Args:
        qs: BettingRecord の QuerySet
    Returns:
        dict: 集計統計
    """
    agg = qs.aggregate(
        total_bet=Sum('bet_amount'),
        total_payout=Sum('payout'),
        total_records=Count('id'),
        total_win=Count('id', filter=Q(is_win=True)),
        total_profit=Sum('profit'),
    )

    total_bet    = agg['total_bet'] or 0
    total_payout = agg['total_payout'] or 0
    total_records = agg['total_records'] or 0
    total_win    = agg['total_win'] or 0
    total_profit = agg['total_profit'] or 0

    roi   = round(total_payout / total_bet * 100, 1) if total_bet > 0 else 0.0
    win_rate = round(total_win / total_records * 100, 1) if total_records > 0 else 0.0

    return {
        'total_bet':     total_bet,
        'total_payout':  total_payout,
        'total_records': total_records,
        'total_win':     total_win,
        'total_profit':  total_profit,
        'roi':           roi,
        'win_rate':      win_rate,
    }


def _monthly_chart_data(qs):
    """
    月次集計データを Chart.js 用に変換する。
    Args:
        qs: BettingRecord の QuerySet
    Returns:
        dict: labels / bet_data / payout_data
    """
    from django.db.models.functions import TruncMonth
    monthly = (
        qs.annotate(month=TruncMonth('race_date'))
          .values('month')
          .annotate(
              bet=Sum('bet_amount'),
              payout=Sum('payout'),
          )
          .order_by('month')
    )
    labels, bet_data, payout_data = [], [], []
    for row in monthly:
        labels.append(row['month'].strftime('%Y-%m') if row['month'] else '')
        bet_data.append(row['bet'] or 0)
        payout_data.append(row['payout'] or 0)
    return {'labels': labels, 'bet_data': bet_data, 'payout_data': payout_data}


class DashboardView(View):
    """
    ダッシュボード画面。実データと月次チャートを表示する。
    """

    def get(self, request):
        """
        DB から馬券記録を取得し集計してダッシュボードを表示する。
        """
        # 全記録（実購入のみ）
        real_qs = BettingRecord.objects.filter(is_simulation=False)
        # 30日以内
        since_30 = now().date() - timedelta(days=30)
        recent_qs = real_qs.filter(race_date__gte=since_30)

        stats_all    = _build_stats(real_qs)
        stats_recent = _build_stats(recent_qs)
        chart_data   = _monthly_chart_data(real_qs)

        # 直近10件
        recent_records = (
            real_qs.filter(is_win__isnull=False)
                   .order_by('-race_date', '-created_at')[:10]
        )

        # 学習データ件数
        training_count = TrainingInfo.objects.count()

        context = {
            'stats_all':       stats_all,
            'stats_recent':    stats_recent,
            'chart_data_json': json.dumps(chart_data, ensure_ascii=False),
            'recent_records':  recent_records,
            'training_count':  training_count,
            # シミュレーション用
            'bet_type_choices': BettingRecord.BET_TYPE_CHOICES,
        }
        return render(request, 'app_folder/dashboard.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class BettingSimulateView(View):
    """
    馬券シミュレーション API。
    POST: シミュレーション記録を登録し損益を返す。
    GET:  過去シミュレーション一覧を返す。
    """

    def get(self, request):
        """シミュレーション一覧を JSON で返す。"""
        records = (
            BettingRecord.objects.filter(is_simulation=True)
                          .order_by('-race_date', '-created_at')[:50]
        )
        data = []
        for r in records:
            data.append({
                'id':          r.id,
                'race_date':   str(r.race_date),
                'race_id':     r.race_id,
                'race_place':  r.race_place or '',
                'race_name':   r.race_name or '',
                'bet_type':    r.get_bet_type_display(),
                'combination': r.combination,
                'bet_amount':  r.bet_amount,
                'odds':        r.odds,
                'is_win':      r.is_win,
                'payout':      r.payout,
                'profit':      r.profit,
            })
        agg_qs = BettingRecord.objects.filter(is_simulation=True)
        stats = _build_stats(agg_qs)
        return JsonResponse({'records': data, 'stats': stats})

    def post(self, request):
        """
        シミュレーション馬券を登録する。
        Body (JSON):
            race_id, race_date, bet_type, combination, bet_amount, odds,
            is_win, payout, race_place (opt), race_name (opt)
        """
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '不正なJSON形式です。'}, status=400)

        required = ['race_id', 'race_date', 'bet_type', 'combination', 'bet_amount']
        for key in required:
            if not body.get(key):
                return JsonResponse({'error': f'{key} は必須です。'}, status=400)

        bet_amount = int(body.get('bet_amount', 100))
        odds       = float(body.get('odds') or 0)
        is_win     = body.get('is_win')  # None / True / False
        payout     = int(body.get('payout', 0))

        # oddsとbet_amountからpayoutを自動計算（payout未入力かつis_win=Trueの場合）
        if is_win is True and payout == 0 and odds > 0:
            payout = int(bet_amount * odds)

        record = BettingRecord.objects.create(
            race_id      = body['race_id'],
            race_date    = body['race_date'],
            race_place   = body.get('race_place') or '',
            race_name    = body.get('race_name') or '',
            bet_type     = body['bet_type'],
            combination  = body['combination'],
            bet_amount   = bet_amount,
            odds         = odds or None,
            is_win       = is_win,
            payout       = payout,
            is_simulation= True,
            memo         = body.get('memo') or '',
        )

        return JsonResponse({
            'id':      record.id,
            'profit':  record.profit,
            'payout':  record.payout,
            'message': 'シミュレーション記録を保存しました。',
        }, status=201)


class BettingRecordView(View):
    """
    実際の馬券記録 CRUD。
    POST: 記録追加
    PATCH: 払い戻し・的中結果更新
    """

    def post(self, request):
        """実際の馬券購入を記録する。"""
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '不正なJSON形式です。'}, status=400)

        required = ['race_id', 'race_date', 'bet_type', 'combination', 'bet_amount']
        for key in required:
            if not body.get(key):
                return JsonResponse({'error': f'{key} は必須です。'}, status=400)

        record = BettingRecord.objects.create(
            race_id      = body['race_id'],
            race_date    = body['race_date'],
            race_place   = body.get('race_place') or '',
            race_name    = body.get('race_name') or '',
            bet_type     = body['bet_type'],
            combination  = body['combination'],
            bet_amount   = int(body.get('bet_amount', 100)),
            odds         = float(body.get('odds') or 0) or None,
            is_simulation= False,
        )
        return JsonResponse({'id': record.id, 'message': '記録を保存しました。'}, status=201)

    def patch(self, request, record_id):
        """
        払い戻し結果を更新する。
        Body: { is_win, payout }
        """
        try:
            record = BettingRecord.objects.get(id=record_id)
        except BettingRecord.DoesNotExist:
            return JsonResponse({'error': '記録が見つかりません。'}, status=404)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '不正なJSON形式です。'}, status=400)

        record.is_win  = body.get('is_win', record.is_win)
        record.payout  = int(body.get('payout', record.payout))
        record.save()
        return JsonResponse({'profit': record.profit})


dashboard_view  = DashboardView.as_view()
simulate_view   = BettingSimulateView.as_view()
betting_view    = BettingRecordView.as_view()
