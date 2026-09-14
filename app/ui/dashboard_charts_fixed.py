"""
نمودارهای داشبورد با تم تاریک
این فایل را جایگزین app/ui/dashboard_charts.py کنید
"""

from app.core.jalali import jalali_date_display_from_iso


def build_financial_balance_chart(data, title="نمای مالی", subtitle=""):
    """نمودار موجودی مالی با تم تاریک"""
    if not data:
        return _empty_chart(title, subtitle)
    
    # ساخت HTML با تم تاریک
    html = f"""
    <html dir="rtl"><head><meta charset="utf-8">
    <style>
        body {{ 
            font-family: Tahoma; 
            margin: 0; 
            padding: 10px; 
            background: #46505f;
            color: #e2e8f0;
        }}
        .title {{ 
            font-size: 14px; 
            font-weight: bold; 
            color: #f8fafc;
            text-align: center;
            margin-bottom: 5px;
        }}
        .subtitle {{ 
            font-size: 11px; 
            color: #64748b;
            text-align: center;
            margin-bottom: 10px;
        }}
        .chart {{ 
            display: flex; 
            justify-content: space-around;
            align-items: flex-end;
            height: 120px;
            padding: 10px;
        }}
        .bar {{ 
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 80px;
        }}
        .bar-value {{ 
            font-size: 10px; 
            color: #e2e8f0;
            margin-bottom: 3px;
        }}
        .bar-box {{ 
            width: 60px;
            background: linear-gradient(to top, #2563eb, #3b82f6);
            border-radius: 4px 4px 0 0;
        }}
        .bar-label {{ 
            font-size: 9px; 
            color: #64748b;
            margin-top: 5px;
            text-align: center;
        }}
    </style></head><body>
    <div class="title">{title}</div>
    """
    
    if subtitle:
        html += f'<div class="subtitle">{subtitle}</div>'
    
    html += '<div class="chart">'
    
    # نمایش داده‌ها
    for key, value in data.items():
        max_val = max(data.values()) if data else 1
        height = int((value / max_val) * 100) if max_val > 0 else 0
        html += f"""
        <div class="bar">
            <div class="bar-value">{value:,}</div>
            <div class="bar-box" style="height: {height}px;"></div>
            <div class="bar-label">{key}</div>
        </div>
        """
    
    html += '</div></body></html>'
    return html


def build_warehouse_value_chart(data, title="ارزش انبار", subtitle=""):
    """نمودار ارزش انبارها با تم تاریک"""
    if not data:
        return _empty_chart(title, subtitle)
    
    html = f"""
    <html dir="rtl"><head><meta charset="utf-8">
    <style>
        body {{ 
            font-family: Tahoma; 
            margin: 0; 
            padding: 10px; 
            background: #46505f;
            color: #e2e8f0;
        }}
        .title {{ 
            font-size: 14px; 
            font-weight: bold; 
            color: #f8fafc;
            text-align: center;
            margin-bottom: 5px;
        }}
        .subtitle {{ 
            font-size: 11px; 
            color: #64748b;
            text-align: center;
            margin-bottom: 10px;
        }}
        .chart {{ 
            display: flex; 
            flex-direction: column;
            gap: 8px;
        }}
        .bar-row {{ 
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .bar-label {{ 
            width: 100px;
            font-size: 10px;
            color: #e2e8f0;
            text-align: right;
        }}
        .bar-track {{ 
            flex: 1;
            height: 20px;
            background: #5b6675;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar-fill {{ 
            height: 100%;
            background: linear-gradient(to right, #16a34a, #22c55e);
            border-radius: 4px;
        }}
        .bar-value {{ 
            width: 100px;
            font-size: 10px;
            color: #e2e8f0;
            text-align: left;
        }}
    </style></head><body>
    <div class="title">{title}</div>
    """
    
    if subtitle:
        html += f'<div class="subtitle">{subtitle}</div>'
    
    html += '<div class="chart">'
    
    max_val = max(d.get('value', 0) for d in data) if data else 1
    
    for item in data[:6]:  # حداکثر 6 مورد
        name = item.get('name', 'نامشخص')
        value = item.get('value', 0)
        width = int((value / max_val) * 100) if max_val > 0 else 0
        html += f"""
        <div class="bar-row">
            <div class="bar-label">{name}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width: {width}%;"></div>
            </div>
            <div class="bar-value">{value:,}</div>
        </div>
        """
    
    html += '</div></body></html>'
    return html


def build_treasury_balance_chart(data, title="صندوق/بانک", subtitle=""):
    """نمودار صندوق و بانک با تم تاریک"""
    if not data:
        return _empty_chart(title, subtitle)
    
    html = f"""
    <html dir="rtl"><head><meta charset="utf-8">
    <style>
        body {{ 
            font-family: Tahoma; 
            margin: 0; 
            padding: 10px; 
            background: #46505f;
            color: #e2e8f0;
        }}
        .title {{ 
            font-size: 14px; 
            font-weight: bold; 
            color: #f8fafc;
            text-align: center;
            margin-bottom: 5px;
        }}
        .subtitle {{ 
            font-size: 11px; 
            color: #64748b;
            text-align: center;
            margin-bottom: 10px;
        }}
        .chart {{ 
            display: flex; 
            justify-content: space-around;
            align-items: flex-end;
            height: 120px;
            padding: 10px;
        }}
        .bar {{ 
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 80px;
        }}
        .bar-value {{ 
            font-size: 10px; 
            color: #e2e8f0;
            margin-bottom: 3px;
        }}
        .bar-box {{ 
            width: 60px;
            background: linear-gradient(to top, #f59e0b, #b45309);
            border-radius: 4px 4px 0 0;
        }}
        .bar-label {{ 
            font-size: 9px; 
            color: #64748b;
            margin-top: 5px;
            text-align: center;
        }}
    </style></head><body>
    <div class="title">{title}</div>
    """
    
    if subtitle:
        html += f'<div class="subtitle">{subtitle}</div>'
    
    html += '<div class="chart">'
    
    for item in data:
        name = item.get('name', 'نامشخص')
        value = item.get('balance', 0)
        max_val = max(d.get('balance', 0) for d in data) if data else 1
        height = int((value / max_val) * 100) if max_val > 0 else 0
        html += f"""
        <div class="bar">
            <div class="bar-value">{value:,}</div>
            <div class="bar-box" style="height: {height}px;"></div>
            <div class="bar-label">{name}</div>
        </div>
        """
    
    html += '</div></body></html>'
    return html


def build_activity_chart(data, title="روند عملیات", subtitle=""):
    """نمودار روند عملیات با تم تاریک"""
    if not data:
        return _empty_chart(title, subtitle)
    
    html = f"""
    <html dir="rtl"><head><meta charset="utf-8">
    <style>
        body {{ 
            font-family: Tahoma; 
            margin: 0; 
            padding: 10px; 
            background: #46505f;
            color: #e2e8f0;
        }}
        .title {{ 
            font-size: 14px; 
            font-weight: bold; 
            color: #f8fafc;
            text-align: center;
            margin-bottom: 5px;
        }}
        .subtitle {{ 
            font-size: 11px; 
            color: #64748b;
            text-align: center;
            margin-bottom: 10px;
        }}
        .chart {{ 
            display: flex; 
            flex-direction: column;
            gap: 5px;
        }}
        .bar-row {{ 
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .bar-label {{ 
            width: 80px;
            font-size: 10px;
            color: #e2e8f0;
            text-align: right;
        }}
        .bar-track {{ 
            flex: 1;
            height: 15px;
            background: #5b6675;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar-fill {{ 
            height: 100%;
            background: linear-gradient(to right, #8b5cf6, #a78bfa);
            border-radius: 4px;
        }}
        .bar-value {{ 
            width: 60px;
            font-size: 10px;
            color: #e2e8f0;
            text-align: left;
        }}
    </style></head><body>
    <div class="title">{title}</div>
    """
    
    if subtitle:
        html += f'<div class="subtitle">{subtitle}</div>'
    
    html += '<div class="chart">'
    
    max_val = max(data.values()) if data else 1
    
    for date, count in data.items():
        width = int((count / max_val) * 100) if max_val > 0 else 0
        html += f"""
        <div class="bar-row">
            <div class="bar-label">{date}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width: {width}%;"></div>
            </div>
            <div class="bar-value">{count}</div>
        </div>
        """
    
    html += '</div></body></html>'
    return html


def _empty_chart(title, subtitle=""):
    """نمودار خالی با تم تاریک"""
    html = f"""
    <html dir="rtl"><head><meta charset="utf-8">
    <style>
        body {{ 
            font-family: Tahoma; 
            margin: 0; 
            padding: 20px; 
            background: #46505f;
            color: #64748b;
            text-align: center;
        }}
        .title {{ 
            font-size: 14px; 
            font-weight: bold; 
            color: #e2e8f0;
            margin-bottom: 10px;
        }}
    </style></head><body>
    <div class="title">{title}</div>
    <div>داده‌ای برای نمایش وجود ندارد</div>
    </body></html>
    """
    return html
