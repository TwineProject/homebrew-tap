cask "twine-app" do
  version "0.2.4"
  sha256 "54ce5032741620a8b4866ef0a2688a29192b35ff8c8d7929318460028219578f"

  url "https://github.com/aravind-n/twine/releases/download/v#{version}/Twine-#{version}-macos-arm64.dmg"
  name "Twine"
  desc "Workspace for coordinating coding agents"
  homepage "https://github.com/aravind-n/twine"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on macos: :tahoe

  app "Twine.app"

  # Twine's saved sessions, transcripts, and workflows are user data.
  # No zap stanza required.
end
