
from sklearn.model_selection import KFold
from sklearn.metrics import ndcg_score
import joblib
import lightgbm as lgb
import os
import glob
import pandas as pd
from django.conf import settings
# import xgboost as xgb
# from catboost import Pool, CatBoostRanker
from sklearn.preprocessing import LabelEncoder

# 共通の列
common_cols = [
    'today_race_date', 'race_id'
    ]

order_cols = [
    'today_race_date', 'race_id', 'horse_number'
    ]

# 結果情報の列項目
define_cols = [
    'today_race_date', 'race_id', 'horse_number', "rank", 
    "race_time", "corner_order", "positions", "positions_tie",
    "pay1", "pay1_tie", "pay123_1", "pay123_2", "pay123_3", "pay123_tie",
    "pay123_12_1", "pay123_12_2", "pay123_12_3", "pay123_12_4_tie", "pay123_12_5_tie",
    "pay12_21", "pay12_21_tie", "pay12_12", "pay12_12_tie",
    "pay123_321", "pay123_321_tie", "pay123_123", "pay123_123_tie"
    ]

target_cols = ['rank', 'rank_relation', 'race_time']
target_col = 'rank_relation'

# --- LightGBM用 カテゴリ変数の自動判定関数 ---
def is_categorical(series):
    if series.dtype == 'object' or pd.api.types.is_categorical_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series) and series.nunique() <= 10:
        return True
    return False

def group_time_series_split(train_df, result_df, n_splits=5):
    """
    Group単位（today_race_date + race_id）で、過去→未来の順でK分割するジェネレーター。
    学習データが未来データを含まないことを保証。
    
    Args:
        df: 入力データ（DataFrame）
        n_splits: 分割数
    
    Yields:
        train_index, val_index
    """
    # 1. Group単位のユニーク取得 + 並び替え
    group_df = result_df.sort_values(by = common_cols)
    groups_list = group_df[common_cols].values
    n_groups = len(groups_list)

    # 2. Group単位でFoldの範囲を決定
    fold_size = n_groups // n_splits
    for i in range(n_splits):
        val_start = i * fold_size
        val_end = val_start + fold_size if i < n_splits - 1 else n_groups

        train_groups = groups_list[:val_start]
        val_groups = groups_list[val_start:val_end]

        train_mask = train_df[common_cols].apply(tuple, axis=1).isin([tuple(g) for g in train_groups])
        val_mask = train_df[common_cols].apply(tuple, axis=1).isin([tuple(g) for g in val_groups])

        yield train_df[train_mask].index, train_df[val_mask].index
    
# CSV出力先の絶対パス
csv_dir = os.path.join(settings.MEDIA_ROOT, "train_csv")
csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
csv_path = max(csv_files, key=os.path.getmtime) if csv_files else None
if csv_path ==  None:
    print(111)

df = pd.read_csv(csv_path)
sort_df = df.sort_values(by = order_cols, ascending=[True, True, True])
result_cols = [col for col in define_cols if col in sort_df.columns]
train_cols = [col for col in sort_df.columns if col not in result_cols]
train_df = sort_df[order_cols + train_cols]
result_df = sort_df[result_cols]
result_df[target_col] = result_df['rank'].apply(lambda x: 30 if x == '1' else (20 if x == '2' else 0))
check_df = sort_df[order_cols]

categorical_cols = []

# 型を整形
for col in train_df.columns:
    try:
        if is_categorical(col, train_df[col]):
            train_df[col] = train_df[col].astype("category")
            categorical_cols.append(col)
        else:
            train_df[col] = train_df[col].astype("float32")
    except Exception as e:
        print(e)
        print(col)
        exit

for col in target_cols:
    if col in result_df.columns:
        # None または NaNをその列の最大値で埋める
        max_value = result_df[col].max()
        result_df[col] = result_df[col].fillna(max_value)
        result_df[col] = result_df[col].astype("float32")

# スコア保存用
scores = []
models = []
n_splits = 5

all_splits = list(group_time_series_split(check_df, n_splits=n_splits))

# 最後のSplitだけテストデータ
train_val_splits = all_splits[:-1]
test_split = all_splits[-1]

# test_splitから取得
X_test_index, Y_test_index = test_split
X_test = train_df.iloc[X_test_index]
Y_test = result_df.iloc[Y_test_index][target_col]
G_test = X_test.groupby('race_id').size().to_list()

# 残りをKFoldループ
for fold_id, (train_index, val_index) in enumerate(train_val_splits):
    X_train = train_df.iloc[train_index]
    X_val = train_df.iloc[val_index]
    Y_train = result_df.iloc[train_index][target_col]
    Y_val = result_df.iloc[val_index][target_col]
    G_train = X_train.groupby('race_id').size().to_list()
    G_val = X_val.groupby('race_id').size().to_list()

    # データセットをLightGBM用に準備
    train_data = lgb.Dataset(X_train, label=Y_train, categorical_feature=categorical_cols, group=G_train)
    val_data = lgb.Dataset(X_val, label=Y_val, categorical_feature=categorical_cols, group=G_val)

    # パラメータ例（競馬Rank予測向け）
    params = {
        'objective': 'lambdarank',
        'metric': 'ndcg',
        'ndcg_at': [1, 3, 5],           # 評価する上位N
        'learning_rate': 0.03,
        'num_leaves': 31,
        'max_depth': -1,
        'min_data_in_leaf': 20,
        'bagging_fraction': 0.8,
        'bagging_freq': 1,
        'feature_fraction': 0.8,
        'lambda_l1': 0.1,
        'lambda_l2': 1.0,
        'min_gain_to_split': 0.1,
        'seed': 42 + fold_id,
        'verbosity': -1,
        'n_jobs': -1
    }

    # 学習
    model = lgb.train(
        params,
        train_data,
        valid_sets=[train_data, val_data],
        num_boost_round=1000,
        early_stopping_rounds=100,
        verbose_eval=100
    )

    # スコア算出
    P_val = model.predict(X_val, num_iteration=model.best_iteration)
    rmse = mean_squared_error(Y_val, P_val, squared=False)

    scores.append(rmse)
    models.append({
        "model": model,
        "fold": fold_id,
        "best_iteration": model.best_iteration
    })

P_test = model.predict(X_test)

test_results = X_test[order_cols].copy()
test_results[target_col] = P_test
test_results = test_results.sort_values(by=["race_id", target_col], ascending=[True, False])

# 予想順位
test_results["predicted_rank"] = test_results.groupby("race_id")["pred_score"].rank(ascending=False, method="first")

print(f"全FoldのRMSE: {scores}")
print(f"平均RMSE: {np.mean(scores):.4f}")
kf = KFold(n_splits=6)
final_predictions = []
base_models = create_base_models(input_data)
for train_index, val_index in kf.split(input_data):
    X_train, X_val = input_data.iloc[train_index], input_data.iloc[val_index]
    y_train, y_val = target_data.iloc[train_index]['着順関連度'], target_data.iloc[val_index]['着順関連度']

    base_predictions = train_and_predict(base_models, X_train, y_train, X_val, y_val)
    stacked_predictions = stacking(base_predictions, y_val)

    final_predictions.extend(stacked_predictions)

target_data['予測スコア'] = final_predictions
accuracy_top2(target_data)


def group_ndcg_score(y_true, y_pred, groups, k):
    scores = []
    start = 0
    for group in groups:
        end = start + group
        group_true = y_true[start:end]
        group_pred = y_pred[start:end]
        if len(group_true) > 1:  # 2つ以上のドキュメントがある場合のみスコアを計算
            score = ndcg_score([group_true], [group_pred], k=max(1, min(k, len(group_true))))
            scores.append(score)
        start = end
    return np.mean(scores) if scores else 0  # スコアが計算されなかった場合は0を返す

def accuracy_top2(target_val):
    # モデル予測スコアでソートし、上位2着の馬を検証
    accuracy= 0
    count = 0
    top2_accuracy = []
    target_val['着 順'] = target_val['着 順'].apply(lambda x: 99 if x == '中止' else (99 if x == '取消' else (99 if x == '除外' else x)))
    target_val['着 順'] = target_val['着 順'].astype(float)
    for race_id in target_val['レースID'].unique():
        race_data = target_val[target_val['レースID'] == race_id]
        race_data['prediction_order'] = race_data['予測スコア'].rank(ascending=False, method='first')
        actual_top2 = race_data.nsmallest(2, '着 順')['馬名']
        predicted_top2 = race_data.nsmallest(2, 'prediction_order')['馬名']
        if set(actual_top2) == set(predicted_top2):
            accuracy = accuracy + 1
        else:
            accuracy = accuracy + 0
        count = count + 1
    mean_top2_accuracy = accuracy / count * 100
    print(f"{accuracy} / {count} * 100 = {mean_top2_accuracy}")

def create_base_models(df):
    global categorical_features
    lgb_model = lgb.LGBMRanker(
        objective='lambdarank',
        metric=['ndcg'],
        n_estimators=2500,
        learning_rate=0.01979240717683409,
        num_leaves=42,
        max_depth=10,
        min_child_samples=150,
        min_data_in_leaf=7,
        extra_tree=True,
        reg_alpha=5.962163920557285e-08,
        reg_lambda=1.0359378057133484,
        max_bin=512
    )

    xgb_model = xgb.XGBRanker(
        objective='rank:ndcg',
        learning_rate=0.1,
        n_estimators=1000,
        max_depth=6,
        min_child_weight=1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='ndcg@2',  # eval_metricをここで指定
        early_stopping_rounds=10  # CatBoostの早期停止をここで設定
    )
    for feature in categorical_features:
        df[feature] = df[feature].astype(str)
        df[feature] = df[feature].fillna("N")
        df[feature] = df[feature].astype('category')

    cat_features_index = [df.columns.get_loc(col) for col in categorical_features]
    cat_model = CatBoostRanker(
        iterations=1000,
        learning_rate=0.1,
        depth=6,
        loss_function='YetiRankPairwise',
        cat_features=cat_features_index,
        eval_metric='NDCG:top=2',  # 'ndcg@2'ではなく'NDCG:top=2'を使用
        early_stopping_rounds=10
    )

    return [lgb_model, xgb_model, cat_model]

def train_and_predict(models, X_train, y_train, X_val, y_val):
    global categorical_features
    X_train['レースID'] = X_train['レースID'].astype(int)
    X_val['レースID'] = X_val['レースID'].astype(int)
    train_query = X_train.groupby(['レースID']).size().values.tolist()
    val_query = X_val.groupby(['レースID']).size().values.tolist()
    cat_train_query = X_train['レースID'].values.tolist()
    cat_val_query = X_val['レースID'].values.tolist()
    predictions = []
    X_train_base = X_train
    y_train_base = y_train
    X_val_base = X_val
    y_val_base = y_val
    for model in models:
        if isinstance(model, lgb.LGBMRanker):
            X_train = X_train_base
            y_train = y_train_base
            X_val = X_val_base
            y_val = y_val_base
            model.fit(X_train, y_train, group=train_query, eval_set=[(X_val, y_val)], eval_group=[val_query], eval_metric=['ndcg'], eval_at=[1,2], callbacks=[lightgbm.early_stopping(stopping_rounds=10)])
        elif isinstance(model, xgb.XGBRanker):
            X_train = X_train_base
            y_train = y_train_base
            X_val = X_val_base
            y_val = y_val_base
            # Label Encoding
            le = LabelEncoder()
            for feature in categorical_features:
                X_train[feature] = le.fit_transform(X_train[feature].astype(str))
                X_val[feature] = le.fit_transform(X_val[feature].astype(str))

            # すべての特徴量を数値型に変換
            numerical_features = [col for col in X_train.columns if col not in categorical_features]
            for feature in numerical_features:
                X_train[feature] = X_train[feature].astype(float)
                X_val[feature] = X_val[feature].astype(float)

            model.fit(X_train, y_train, group=train_query, eval_set=[(X_val, y_val)], eval_group=[val_query])
        else:  # CatBoostRanker
            cat_features_index = [X_train.columns.get_loc(col) for col in categorical_features]
            X_train = X_train_base
            y_train = y_train_base
            X_val = X_val_base
            y_val = y_val_base
            for feature in categorical_features:
                X_train[feature] = X_train[feature].astype(str)
                X_train[feature] = X_train[feature].fillna("N")
                X_train[feature] = X_train[feature].astype('category')
                X_val[feature] = X_val[feature].astype(str)
                X_val[feature] = X_val[feature].fillna("N")
                X_val[feature] = X_val[feature].astype('category')

            # すべての特徴量を数値型に変換
            numerical_features = [col for col in X_train.columns if col not in categorical_features]
            for feature in numerical_features:
                X_train[feature] = X_train[feature].fillna(0).astype(float)
                X_val[feature] = X_val[feature].fillna(0).astype(float)

            # 評価用データセットの準備
            train_dataset = Pool(
                data=X_train,
                label=y_train,
                group_id=cat_train_query,  # 評価用データのグループID
                cat_features=cat_features_index  # カテゴリカル特徴量のインデックス
            )
            # 評価用データセットの準備
            eval_dataset = Pool(
                data=X_val,
                label=y_val,
                group_id=cat_val_query,  # 評価用データのグループID
                cat_features=cat_features_index  # カテゴリカル特徴量のインデックス
            )

            model.fit(train_dataset, eval_set=eval_dataset, use_best_model=True)

        predictions.append(model.predict(X_val))

    return np.array(predictions).T

def stacking(base_predictions, y_true):
    meta_model = LogisticRegression()
    meta_model.fit(base_predictions, y_true)
    return meta_model.predict_proba(base_predictions)[:, 1]

def enhanced_network(input_data, target_data):
    pass


def bk():
    def NetWork(input_data, target_data):
        global categorical_features
        # 交差検証
        # K-フォールドクロスバリデーションの設定 , shuffle=True, random_state=42
        kf = KFold(n_splits=6)

        # 各フォールドの結果を保持するリスト
        ndcg_scores = []
        for train_index, test_index in kf.split(input_data):
            train, train_val = input_data.iloc[train_index], input_data.iloc[test_index]
            target, target_val = target_data.iloc[train_index], target_data.iloc[test_index]
            train_query = train.groupby(['レースID']).size().values.tolist()
            valid_query = train_val.groupby(['レースID']).size().values.tolist()

            model = lightgbm.LGBMRanker(
                objective = 'lambdarank',
                metric=['ndcg'],
                n_estimators = 2500,
                learning_rate = 0.01979240717683409,
                num_leaves = 42,
                max_depth = 10,
                min_child_samples = 150,
                min_data_in_leaf = 7,
                extra_tree = True,
                # lambda_l1 = 5.962163920557285e-08,
                # lambda_l2 = 1.03593780571334845,
                reg_alpha = 5.962163920557285e-08,   # reg_alphaにL1正則化の値を設定
                reg_lambda = 1.0359378057133484,     # reg_lambdaにL2正則化の値を設定
                max_bin = 512,
                categorical_feature=categorical_features
                # random_state = 100,
                # 'feature_fraction': 0.7534411453169909,
                # 'bagging_fraction': 0.9758395648702864,
                # 'bagging_freq': 4,
                # 'feature_pre_filter': False,
            )

            model.fit(train, target['着順関連度'],
                group=train_query,
                eval_set=[(train_val, target_val['着順関連度'])],
                eval_group=[valid_query],
                callbacks=[lightgbm.early_stopping(stopping_rounds=10)],
                eval_metric=['ndcg'],
                eval_at=[1,2],
                categorical_feature=categorical_features
                )

            # テストデータでの予測
            y_pred = model.predict(train_val)
            y_true = target_val['着順関連度'].values
            groups = train_val.groupby(['レースID']).size().values
            ndcg = group_ndcg_score(y_true, y_pred, groups, 2)
            ndcg_scores.append(ndcg)

        # 平均NDCGの計算
        mean_ndcg = np.mean(ndcg_scores)
        target_val = pd.DataFrame(target_val)
        y_pred = pd.DataFrame(y_pred)
        col = target_val.columns.append(pd.Index(['予測スコア']))
        target_val = target_val.reset_index(drop=True)
        y_pred = y_pred.reset_index(drop=True)
        target_val = pd.concat([target_val, y_pred], axis = 1 , ignore_index = True)
        target_val.columns = col
        target_val.to_csv('/content/drive/MyDrive/MachineLearning/input/Horsing/predict.csv', index=False)

        accuracy_top2(target_val)

        return model, mean_ndcg


model, mean_ndcg = enhanced_network(input_data, target_data)

# モデルを保存
joblib.dump(model, '/content/drive/MyDrive/MachineLearning/input/Horsing/lightgbm_model.pkl')

print(mean_ndcg)

