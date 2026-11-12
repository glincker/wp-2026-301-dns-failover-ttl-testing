import java.io.*; import java.net.*; import java.util.concurrent.*;
/** Java client. Usage: Client HOST PORT MODE DURATION_S INTERVAL_MS CONNECT_TIMEOUT|none CAP_S. HttpURLConnection, one request per loop. */
public class Client {
  static void out(String s) { System.out.println(s); System.out.flush(); }
  public static void main(String[] a) throws Exception {
    String host = a[0], port = a[1], mode = a[2];
    double dur = Double.parseDouble(a[3]); long iv = Long.parseLong(a[4]); long cap = (long) Double.parseDouble(a[6]);
    int cto = a[5].equals("none") ? 0 : (int) (Double.parseDouble(a[5]) * 1000);
    StringBuilder sb = new StringBuilder();
    try { for (InetAddress x : InetAddress.getAllByName(host)) sb.append(sb.length() > 0 ? "," : "").append("\"").append(x.getHostAddress()).append("\""); } catch (Exception e) {}
    out("{\"order\":[" + sb + "]}");
    long end = System.currentTimeMillis() + (long) (dur * 1000);
    ExecutorService ex = Executors.newCachedThreadPool(r -> { Thread t = new Thread(r); t.setDaemon(true); return t; });
    while (true) {
      long t = System.currentTimeMillis();
      Future<String> f = ex.submit(() -> {
        HttpURLConnection c = (HttpURLConnection) new URL("http://" + host + ":" + port + "/").openConnection();
        if (cto > 0) c.setConnectTimeout(cto);
        try (BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream()))) { return r.readLine().trim(); }
      });
      String res;
      try { res = "\"body\":\"" + f.get(cap, TimeUnit.SECONDS) + "\""; }
      catch (TimeoutException e) { res = "\"err\":\"cap\""; }
      catch (Exception e) { res = "\"err\":\"" + (e.getCause() != null ? e.getCause().getClass().getSimpleName() : "error") + "\""; }
      out("{\"t\":" + t + ",\"ms\":" + (System.currentTimeMillis() - t) + "," + res + "}");
      if (mode.equals("once") || System.currentTimeMillis() >= end) { System.exit(0); }
      Thread.sleep(Math.max(0, iv - (System.currentTimeMillis() - t)));
    }
  }
}
