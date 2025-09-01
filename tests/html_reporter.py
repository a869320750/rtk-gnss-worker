"""
HTML测试报告生成器
"""

import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path


class HTMLTestReporter:
    """HTML测试报告生成器"""
    
    def __init__(self, output_dir="reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.test_results = []
        self.start_time = None
        self.end_time = None
        
        # 测试类型描述
        self.test_descriptions = {
            'unit': {
                'title': '单元测试 (Unit Tests)',
                'description': '测试独立模块的功能，包括配置管理、数据处理、串口通信等核心组件',
                'icon': '🔧'
            },
            'integration': {
                'title': '集成测试 (Integration Tests)', 
                'description': '测试模块间协作，包括NTRIP客户端、数据流处理、线程协调等',
                'icon': '🔗'
            },
            'real-integration': {
                'title': '真实集成测试 (Real Integration Tests)',
                'description': '使用真实NTRIP服务和串口设备进行端到端测试',
                'icon': '🌍'
            },
            'system': {
                'title': '系统测试 (System Tests)',
                'description': '验证完整系统在真实环境下的功能和性能',
                'icon': '🌐'
            },
            'architecture': {
                'title': '架构测试 (Architecture Tests)',
                'description': '验证系统架构设计、双线程处理、异常恢复等关键架构特性',
                'icon': '🏗️'
            },
            'all': {
                'title': '完整测试套件 (Full Test Suite)',
                'description': '执行所有类型的测试，确保系统完整性和稳定性',
                'icon': '🚀'
            }
        }
    
    def start_test_session(self, test_type='all'):
        """开始测试会话"""
        self.start_time = datetime.datetime.now()
        self.test_type = test_type
        
        print(f"{self.test_descriptions[test_type]['icon']} 开始 {self.test_descriptions[test_type]['title']}")
        print(f"📝 描述: {self.test_descriptions[test_type]['description']}")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def add_test_result(self, test_name, status, command=None, output=None, error=None, duration=None):
        """添加测试结果"""
        result = {
            'name': test_name,
            'status': status,  # 'success', 'failure', 'error', 'skipped'
            'command': command,
            'output': output,
            'error': error,
            'duration': duration,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.test_results.append(result)
    
    def run_command_with_logging(self, command, test_name, timeout=300):
        """执行命令并记录详细日志"""
        start_time = time.time()
        
        print(f"🔄 执行: {test_name}")
        print(f"💻 命令: {command}")
        
        try:
            # 执行命令并捕获输出
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    output_lines.append(line)
                    print(f"  📄 {line}")
            
            # 等待进程完成
            return_code = process.wait(timeout=timeout)
            duration = time.time() - start_time
            
            full_output = '\n'.join(output_lines)
            
            if return_code == 0:
                status = 'success'
                print(f"✅ {test_name} 通过 (耗时: {duration:.2f}s)")
            else:
                status = 'failure'
                print(f"❌ {test_name} 失败 (耗时: {duration:.2f}s, 退出码: {return_code})")
            
            self.add_test_result(
                test_name=test_name,
                status=status,
                command=command,
                output=full_output,
                duration=duration
            )
            
            return status == 'success'
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {test_name} 超时 (耗时: {duration:.2f}s)")
            self.add_test_result(
                test_name=test_name,
                status='error',
                command=command,
                error=f"测试超时 ({timeout}s)",
                duration=duration
            )
            return False
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {test_name} 异常: {str(e)}")
            self.add_test_result(
                test_name=test_name,
                status='error',
                command=command,
                error=str(e),
                duration=duration
            )
            return False
    
    def end_test_session(self):
        """结束测试会话"""
        self.end_time = datetime.datetime.now()
        duration = self.end_time - self.start_time
        
        # 统计结果
        total_tests = len(self.test_results)
        success_count = len([r for r in self.test_results if r['status'] == 'success'])
        failure_count = len([r for r in self.test_results if r['status'] == 'failure'])
        error_count = len([r for r in self.test_results if r['status'] == 'error'])
        
        print("\n" + "=" * 80)
        print(f"📊 测试会话完成")
        print(f"⏰ 结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总耗时: {duration}")
        print(f"📈 测试统计:")
        print(f"  - 总计: {total_tests}")
        print(f"  - 成功: {success_count} ✅")
        print(f"  - 失败: {failure_count} ❌")
        print(f"  - 错误: {error_count} 💥")
        
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
        print(f"  - 成功率: {success_rate:.1f}%")
        
        return success_count == total_tests
    
    def generate_html_report(self, filename=None):
        """生成HTML报告"""
        if filename is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"test_report_{self.test_type}_{timestamp}.html"
        
        report_path = self.output_dir / filename
        
        # 计算统计信息
        total_tests = len(self.test_results)
        success_count = len([r for r in self.test_results if r['status'] == 'success'])
        failure_count = len([r for r in self.test_results if r['status'] == 'failure'])
        error_count = len([r for r in self.test_results if r['status'] == 'error'])
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
        
        total_duration = self.end_time - self.start_time if self.end_time else datetime.timedelta()
        
        # 生成HTML内容
        html_content = self._generate_html_template(
            test_type=self.test_type,
            total_tests=total_tests,
            success_count=success_count,
            failure_count=failure_count,
            error_count=error_count,
            success_rate=success_rate,
            total_duration=total_duration,
            start_time=self.start_time,
            end_time=self.end_time
        )
        
        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML报告已生成: {report_path}")
        return report_path
    
    def _generate_html_template(self, **kwargs):
        """生成HTML模板"""
        test_info = self.test_descriptions.get(kwargs['test_type'], self.test_descriptions['all'])
        
        # 生成测试结果的HTML
        test_results_html = ""
        for i, result in enumerate(self.test_results, 1):
            status_class = {
                'success': 'success',
                'failure': 'danger', 
                'error': 'warning',
                'skipped': 'secondary'
            }.get(result['status'], 'secondary')
            
            status_icon = {
                'success': '✅',
                'failure': '❌',
                'error': '💥',
                'skipped': '⏭️'
            }.get(result['status'], '❓')
            
            # 处理输出和错误信息
            output_content = ""
            if result.get('output'):
                output_content = f"""
                <div class="mt-2">
                    <h6>执行输出:</h6>
                    <pre class="output-log">{result['output']}</pre>
                </div>
                """
            
            if result.get('error'):
                output_content += f"""
                <div class="mt-2">
                    <h6 class="text-danger">错误信息:</h6>
                    <pre class="error-log">{result['error']}</pre>
                </div>
                """
            
            test_results_html += f"""
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <span class="badge badge-{status_class} mr-2">{status_icon}</span>
                        测试 #{i}: {result['name']}
                    </h5>
                    <small class="text-muted">
                        {result.get('duration', 0):.2f}s
                    </small>
                </div>
                <div class="card-body">
                    {f'<p><strong>执行命令:</strong> <code>{result["command"]}</code></p>' if result.get('command') else ''}
                    <p><strong>执行时间:</strong> {result['timestamp']}</p>
                    {output_content}
                </div>
            </div>
            """
        
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RTK GNSS Worker 测试报告</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 0;
        }}
        .stats-card {{
            border: none;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            transition: all 0.3s ease;
        }}
        .stats-card:hover {{
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            transform: translateY(-0.125rem);
        }}
        .output-log {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.25rem;
            padding: 0.75rem;
            max-height: 300px;
            overflow-y: auto;
            font-size: 0.875rem;
            white-space: pre-wrap;
        }}
        .error-log {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.25rem;
            padding: 0.75rem;
            max-height: 300px;
            overflow-y: auto;
            font-size: 0.875rem;
            white-space: pre-wrap;
        }}
        .progress-custom {{
            height: 1.5rem;
        }}
    </style>
</head>
<body>
    <!-- 报告头部 -->
    <div class="report-header">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <h1 class="display-4 mb-0">{test_info['icon']} RTK GNSS Worker</h1>
                    <h2 class="h4 mb-2">{test_info['title']}</h2>
                    <p class="lead mb-0">{test_info['description']}</p>
                </div>
                <div class="col-md-4 text-right">
                    <div class="badge badge-light badge-pill px-3 py-2">
                        <i class="fas fa-calendar-alt mr-1"></i>
                        {kwargs['start_time'].strftime('%Y-%m-%d %H:%M:%S') if kwargs['start_time'] else 'N/A'}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container mt-4">
        <!-- 测试统计 -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card stats-card text-center">
                    <div class="card-body">
                        <h2 class="text-primary">{kwargs['total_tests']}</h2>
                        <p class="card-text">总测试数</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card text-center">
                    <div class="card-body">
                        <h2 class="text-success">{kwargs['success_count']}</h2>
                        <p class="card-text">成功</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card text-center">
                    <div class="card-body">
                        <h2 class="text-danger">{kwargs['failure_count']}</h2>
                        <p class="card-text">失败</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card text-center">
                    <div class="card-body">
                        <h2 class="text-warning">{kwargs['error_count']}</h2>
                        <p class="card-text">错误</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 成功率和耗时 -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">测试成功率</h5>
                        <div class="progress progress-custom">
                            <div class="progress-bar bg-success" role="progressbar" 
                                 style="width: {kwargs['success_rate']:.1f}%" 
                                 aria-valuenow="{kwargs['success_rate']:.1f}" 
                                 aria-valuemin="0" aria-valuemax="100">
                                {kwargs['success_rate']:.1f}%
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">总耗时</h5>
                        <h3 class="text-info">{kwargs['total_duration']}</h3>
                        <small class="text-muted">
                            开始: {kwargs['start_time'].strftime('%H:%M:%S') if kwargs['start_time'] else 'N/A'} | 
                            结束: {kwargs['end_time'].strftime('%H:%M:%S') if kwargs['end_time'] else 'N/A'}
                        </small>
                    </div>
                </div>
            </div>
        </div>

        <!-- 测试详情 -->
        <div class="row">
            <div class="col-12">
                <h3>📋 测试详情</h3>
                {test_results_html}
            </div>
        </div>
    </div>

    <!-- 页脚 -->
    <footer class="bg-light py-4 mt-5">
        <div class="container text-center">
            <p class="text-muted mb-0">
                🔧 RTK GNSS Worker 测试报告 | 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """
