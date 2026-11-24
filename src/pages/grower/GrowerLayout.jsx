import { Outlet } from 'react-router-dom';
import Header from '../../components/Header.jsx';
import BottomNav from '../../components/BottomNav.jsx';

export default function GrowerLayout() {
  return <><Header /><main className="fg-grower-page fg-grower-content"><Outlet /></main><BottomNav /></>;
}
