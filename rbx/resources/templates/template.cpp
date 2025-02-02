#include <bits/stdc++.h>

using namespace std;
{% if problem_test_type == 'multiNumber' %}
void solve(int tn) {

}
{% endif %}
int32_t main()
{
  ios::sync_with_stdio(false);
  cin.tie(0);
  {% if problem_test_type == 'multiNumber' %}
  int T;
  cin >> T;
  for (int i = 1; i <= T; i++)
    solve(i);
  {% endif %}
}
