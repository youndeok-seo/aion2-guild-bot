import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from fastapi.responses import Response
import io
import platform


if platform.system() == 'Windows':
    rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    rcParams['font.family'] = 'AppleGothic'
else:
    rcParams['font.family'] = 'NanumGothic'

rcParams['axes.unicode_minus'] = False


def generate_combat_power_chart(character_name: str, history: list) -> Response:
    if not history:
        raise ValueError("기록된 데이터가 없습니다")

    dates = [h.recorded_at for h in history]
    powers = [h.combat_power for h in history]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    ax.plot(dates, powers, marker='o', linewidth=2, color='#7F77DD', markersize=6)
    ax.fill_between(dates, powers, alpha=0.2, color='#7F77DD')

    ax.set_title(f'{character_name} 전투력 변화', fontsize=14, fontweight='bold')
    ax.set_xlabel('날짜')
    ax.set_ylabel('전투력')
    ax.grid(True, alpha=0.3)

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return Response(content=buf.read(), media_type="image/png")
