from django import forms
from .models import CustomUser, TrainingInfo
from datetime import datetime, timedelta
# app_folder/forms.py


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'user_name',
            'placeholder': 'ユーザー'
        })
    )
    password = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class': 'user_password',
            'placeholder': 'パスワード'
        })
    )
    mail = forms.EmailField(  # CharField → EmailField に変更
        max_length=128,
        widget=forms.EmailInput(attrs={  # PasswordInput ではなく、EmailInput に変更
            'class': 'user_mail',
            'placeholder': 'メール'
        })
    )

    def save(self):
        # フォームが有効であればユーザーを保存
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        email = self.cleaned_data['mail']

        user = CustomUser.objects.create_user(username=username, email=email)  # create_user でユーザー作成
        user.set_password(password)  # パスワードをハッシュ化
        user.save()  # 保存

        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'user_name',
            'placeholder': 'ユーザー'
        })
    )
    password = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class': 'user_password',
            'placeholder': 'パスワード'
        })
    )

class GetDataForm(forms.Form):
    # 1ヶ月前の日付
    one_month_ago = datetime.today() - timedelta(days=30)
    
    # 現在の日付
    today = datetime.today()

    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'yyyy-mm-dd'}),
        required=True,
        input_formats=['%Y-%m-%d'],
        initial=one_month_ago.date() ,
    )
    
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'yyyy-mm-dd'}),
        required=True,
        input_formats=['%Y-%m-%d'],
        initial=today.date(),
    )

    date_pair = forms.CharField(
        required=False
    )
    
    flg = forms.BooleanField(
        required=False,  # このフィールドが必須でないことを示す
        initial=False,  # デフォルト値をFalseに設定
    )

class TrainForm(forms.Form):
        # 1ヶ月前の日付
    one_month_ago = datetime.today() - timedelta(days=30)
    
    # 現在の日付
    today = datetime.today()

    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'yyyy-mm-dd'}),
        required=True,
        input_formats=['%Y-%m-%d'],
        initial=one_month_ago.date() ,
    )
    
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'yyyy-mm-dd'}),
        required=True,
        input_formats=['%Y-%m-%d'],
        initial=today.date(),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 分類ごとのフィールドリストを初期化
        race_basic_fields = []
        past_horse_fields = []
        past_jockey_fields = []
        result_fields = []

        # TrainingInfoモデルのフィールド取得
        fields = [
            field for field in TrainingInfo._meta.get_fields()
            if not (field.auto_created or field.is_relation)
        ]

        # 全選択を作成
        race_basic_fields.append(('select_all_basic', '【当日】全選択'))
        past_horse_fields.append(('select_all_horse', '【過去履歴】全選択(馬)'))
        past_jockey_fields.append(('select_all_jockey', '【過去履歴】全選択(騎手)'))
        result_fields.append(('select_all_result', '【結果】全選択'))
        for field in fields:
            name = field.name
            verbose = field.verbose_name

            # カテゴリ判定ロジック（フィールド名やメタデータに基づく分類）
            if verbose.startswith('【当日】'):
                race_basic_fields.append((name, verbose))
            elif verbose.endswith('(馬)'):
                past_horse_fields.append((name, verbose))
            elif verbose.endswith('(騎手)'):
                past_jockey_fields.append((name, verbose))
            else:
                result_fields.append((name, verbose))

        # カテゴリごとの MultipleChoiceField を動的に追加
        self.fields['race_basic'] = forms.MultipleChoiceField(
            choices=race_basic_fields,
            widget=forms.CheckboxSelectMultiple(
                attrs={'class': 'checkbox-font'}
            ),
            label='レース基本情報',
            required=False
        )
        self.fields['past_horse'] = forms.MultipleChoiceField(
            choices=past_horse_fields,
            widget=forms.CheckboxSelectMultiple(
                attrs={'class': 'checkbox-font'}
            ),
            label='過去レース情報（馬）',
            required=False
        )
        self.fields['past_jockey'] = forms.MultipleChoiceField(
            choices=past_jockey_fields,
            widget=forms.CheckboxSelectMultiple(
                attrs={'class': 'checkbox-font'}
            ),
            label='過去レース情報（騎手）',
            required=False
        )
        self.fields['result_info'] = forms.MultipleChoiceField(
            choices=result_fields,
            widget=forms.CheckboxSelectMultiple(
                attrs={'class': 'checkbox-font'}
            ),
            label='結果情報',
            required=False
        )