cask "twine-app" do
  version "0.2.3"
  sha256 "1a6316deb3b3d0752be99faf87645b4bc2d819d33503c4e3a1a596c59d8a592f"

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
